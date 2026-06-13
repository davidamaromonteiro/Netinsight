"""Integration tests for the authentication flow.

Tests end-to-end flows: register → login → protected endpoint access.
Uses the same mock strategy as unit tests but chains multiple endpoint
calls together to verify complete user workflows.
"""

import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Mock slowapi / limiter BEFORE importing auth module.
# The ``@limiter.limit("5/minute")`` decorator on ``login()`` fails at
# import time because the function lacks a ``request`` parameter.
# We pre-populate ``sys.modules`` with a stub ``slowapi`` package so that
# ``app.core.limiter`` receives a no-op ``Limiter`` class, which in turn
# makes ``@limiter.limit(...)`` a pass-through decorator.
# ---------------------------------------------------------------------------
_slowapi = MagicMock()
_slowapi.__version__ = "0.1.9"
_limiter_cls = MagicMock()
_limiter_instance = MagicMock()
_limiter_instance.limit = MagicMock(return_value=lambda fn: fn)
_limiter_cls.return_value = _limiter_instance
_slowapi.Limiter = _limiter_cls
_slowapi.util = MagicMock()
_slowapi.util.get_remote_address = MagicMock(return_value="127.0.0.1")

# Prevent slowapi and limiter modules from being imported for real
for mod in list(sys.modules):
    if mod == "slowapi" or mod.startswith("slowapi."):
        sys.modules.pop(mod, None)
    if mod.startswith("app.core.limiter"):
        sys.modules.pop(mod, None)
sys.modules["slowapi"] = _slowapi
sys.modules["slowapi.util"] = _slowapi.util

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.v1.auth import register, login
from app.api.v1.campaigns import list_campaigns
from app.api.deps import get_current_user, require_auth
from app.schemas.user import UserCreate, UserLogin

# Restore sys.modules so that other test modules (e.g. test_health.py
# which imports ``app.main`` → ``slowapi.errors``) can find the real
# ``slowapi`` package.  The ``app.api.v1.auth`` module has already been
# loaded with our mocked limiter — that is fine for these tests.
sys.modules.pop("slowapi", None)
sys.modules.pop("slowapi.util", None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_user(email="test@test.com", is_active=True):
    """Create a MagicMock simulating a Beanie User document."""
    user = MagicMock()
    user.id = "user-flow-001"
    user.email = email
    user.full_name = "Flow User"
    user.role = "analyst"
    user.is_active = is_active
    user.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    user.insert = AsyncMock()
    return user


def _build_mock_user_class(find_one_result=None, return_value=None):
    """Build a MagicMock for the User model class."""
    MockUser = MagicMock(name="User")
    MockUser.find_one = AsyncMock(return_value=find_one_result)
    MockUser.email = MagicMock()
    if return_value is not None:
        MockUser.return_value = return_value
    return MockUser


def _mock_auth_user(email="tester@netinsight.io"):
    """Mock authenticated user for protected endpoints."""
    user = MagicMock()
    user.email = email
    user.id = "usr-001"
    user.role = "analyst"
    return user


# ---------------------------------------------------------------------------
# Test: register + login full flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_then_login():
    """Complete auth flow: register a new user then immediately login.

    Simulates a real user journey: POST /auth/register → POST /auth/login.
    Both calls interact with the same (mocked) User collection.
    """
    mock_user = _mock_user(email="flow@test.com")

    # --- Step 1: Register a new user ---
    MockUser = _build_mock_user_class(find_one_result=None, return_value=mock_user)

    with patch("app.api.v1.auth.User", MockUser), \
         patch("app.api.v1.auth.hash_password", return_value="hashed_xyz"):
        register_payload = UserCreate(
            email="flow@test.com",
            password="securepass123",
            full_name="Flow User",
        )
        reg_result = await register(register_payload)

    assert reg_result.email == "flow@test.com"
    assert reg_result.id == "user-flow-001"
    assert reg_result.full_name == "Flow User"
    assert reg_result.role == "analyst"
    assert reg_result.is_active is True
    mock_user.insert.assert_awaited_once()

    # --- Step 2: Login with the same credentials ---
    MockUser2 = _build_mock_user_class(find_one_result=mock_user)
    mock_request = MagicMock()  # Request object required by limiter

    with patch("app.api.v1.auth.User", MockUser2), \
         patch("app.api.v1.auth.verify_password", return_value=True), \
         patch("app.api.v1.auth.create_access_token", return_value="jwt-flow-token"):
        login_payload = UserLogin(email="flow@test.com", password="securepass123")
        login_result = await login(mock_request, login_payload)

    assert login_result.access_token == "jwt-flow-token"
    assert login_result.token_type == "bearer"


# ---------------------------------------------------------------------------
# Test: invalid token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_invalid_token():
    """Access with a garbage JWT token: get_current_user returns None,
    and require_auth raises 401.

    Simulates: client sends a Bearer token that cannot be decoded.
    """
    creds = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="garbage.invalid.token"
    )

    # decode_access_token returns None for garbage input → user is None
    with patch("app.api.deps.decode_access_token", return_value=None) as mock_decode:
        user = await get_current_user(credentials=creds)

    # The decode was attempted but returned None
    mock_decode.assert_called_once()
    assert user is None

    # require_auth must reject a None user with 401
    with pytest.raises(HTTPException) as exc_info:
        await require_auth(user=None)
    assert exc_info.value.status_code == 401
    assert "Authentication required" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Test: protected endpoint without token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_access_protected_endpoint_without_token():
    """No token provided → get_current_user returns None → require_auth raises 401.

    Simulates: client hits GET /campaigns/ without any Authorization header.
    """
    # No credentials passed → get_current_user returns None
    user = await get_current_user(credentials=None)
    assert user is None

    # require_auth must reject with 401
    with pytest.raises(HTTPException) as exc_info:
        await require_auth(user=user)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Authentication required"


# ---------------------------------------------------------------------------
# Test: protected endpoint with valid token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_access_protected_endpoint_with_token():
    """Valid JWT → get_current_user resolves the user → protected endpoint returns 200.

    Simulates: client sends a valid Bearer token, the token decodes correctly,
    User.find_one finds the matching user, and GET /campaigns/ returns data.
    """
    # Build a mock user that get_current_user will return
    mock_user = _mock_user(email="auth@test.com")
    MockUserForAuth = _build_mock_user_class(find_one_result=mock_user)

    # Simulate a valid token decode
    with patch("app.api.deps.User", MockUserForAuth), \
         patch("app.api.deps.decode_access_token",
               return_value={"sub": "auth@test.com", "role": "analyst"}):
        creds = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid.jwt.token"
        )
        authenticated_user = await get_current_user(credentials=creds)

    assert authenticated_user is not None
    assert authenticated_user.email == "auth@test.com"

    # Now use this user to access a protected endpoint
    auth_user = _mock_auth_user()

    MockCampaign = MagicMock(name="Campaign")
    chain = MagicMock()
    chain.sort.return_value = chain
    chain.to_list = AsyncMock(return_value=[])
    MockCampaign.find.return_value = chain
    MockCampaign.created_at = MagicMock()

    with patch("app.api.v1.campaigns.Campaign", MockCampaign):
        result = await list_campaigns(user=auth_user)

    # No exception → 200 OK
    assert isinstance(result, list)
    assert result == []


# ---------------------------------------------------------------------------
# Additional: real JWT round-trip with security module
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_jwt_create_and_decode_roundtrip():
    """Verify that a token created by create_access_token can be decoded
    by decode_access_token — a real JWT round-trip (no mocking)."""
    from app.core.security import create_access_token, decode_access_token

    token = create_access_token(data={"sub": "roundtrip@test.com", "role": "analyst"})
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 20

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "roundtrip@test.com"
    assert payload["role"] == "analyst"
    assert "exp" in payload
