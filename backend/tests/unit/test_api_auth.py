"""Unit tests for authentication API endpoints.

Tests call the async router functions directly because FastAPI's
``TestClient`` does not support the Beanie async lifespan.  All
Beanie ``User`` operations are mocked.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request

from app.api.v1.auth import register, login
from app.schemas.user import UserCreate, UserLogin


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_request():
    """Create a minimal mock of ``fastapi.Request`` for calling endpoints directly."""
    req = MagicMock(spec=Request)
    req.client = MagicMock()
    req.client.host = "127.0.0.1"
    return req

def _mock_user(email="test@test.com", is_active=True):
    """Create a MagicMock simulating a Beanie User document instance."""
    user = MagicMock()
    user.id = "user-mock-001"
    user.email = email
    user.full_name = "Test User"
    user.role = "analyst"
    user.is_active = is_active
    user.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    user.insert = AsyncMock()
    return user


def _build_mock_user_class(return_value=None, find_one_result=None):
    """Build a MagicMock that replaces ``User`` in the auth module.

    Parameters
    ----------
    return_value : MagicMock | None
        Instance returned by ``User(...)``.
    find_one_result : MagicMock | None
        Value returned by ``await User.find_one(...)``.
    """
    MockUser = MagicMock(name="User")
    MockUser.find_one = AsyncMock(return_value=find_one_result)
    # MockUser.email is needed for ``User.email == payload.email`` expressions
    MockUser.email = MagicMock()
    if return_value is not None:
        MockUser.return_value = return_value
    return MockUser


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_success():
    """POST /api/v1/auth/register — 201, returns UserResponse."""
    mock_user = _mock_user()
    MockUser = _build_mock_user_class(
        return_value=mock_user,
        find_one_result=None,  # no existing user
    )

    with patch("app.api.v1.auth.User", MockUser), \
         patch("app.api.v1.auth.hash_password", return_value="hashed_xyz"):
        payload = UserCreate(
            email="test@test.com",
            password="password123",
            full_name="Test User",
        )
        result = await register(payload)

    assert result.id == "user-mock-001"
    assert result.email == "test@test.com"
    assert result.full_name == "Test User"
    assert result.role == "analyst"
    assert result.is_active is True
    mock_user.insert.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_duplicate_email():
    """POST /api/v1/auth/register — 409 when email already exists."""
    existing = _mock_user(email="dup@test.com")
    MockUser = _build_mock_user_class(find_one_result=existing)

    with patch("app.api.v1.auth.User", MockUser):
        payload = UserCreate(email="dup@test.com", password="password123")
        with pytest.raises(HTTPException) as exc_info:
            await register(payload)

    assert exc_info.value.status_code == 409
    assert "already registered" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success():
    """POST /api/v1/auth/login — 200, returns TokenResponse with access_token."""
    mock_user = _mock_user()
    MockUser = _build_mock_user_class(find_one_result=mock_user)

    with patch("app.api.v1.auth.User", MockUser), \
         patch("app.api.v1.auth.verify_password", return_value=True), \
         patch("app.api.v1.auth.create_access_token", return_value="jwt-fake-token"):
        payload = UserLogin(email="test@test.com", password="correct")
        result = await login(_mock_request(), payload)

    assert result.access_token == "jwt-fake-token"
    assert result.token_type == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password():
    """POST /api/v1/auth/login — 401 when password is incorrect."""
    mock_user = _mock_user()
    MockUser = _build_mock_user_class(find_one_result=mock_user)

    with patch("app.api.v1.auth.User", MockUser), \
         patch("app.api.v1.auth.verify_password", return_value=False):
        payload = UserLogin(email="test@test.com", password="wrong")
        with pytest.raises(HTTPException) as exc_info:
            await login(_mock_request(), payload)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user():
    """POST /api/v1/auth/login — 401 when user does not exist."""
    MockUser = _build_mock_user_class(find_one_result=None)

    with patch("app.api.v1.auth.User", MockUser):
        payload = UserLogin(email="nobody@test.com", password="whatever")
        with pytest.raises(HTTPException) as exc_info:
            await login(_mock_request(), payload)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_login_disabled_account():
    """POST /api/v1/auth/login — 403 when account is disabled."""
    mock_user = _mock_user(is_active=False)
    MockUser = _build_mock_user_class(find_one_result=mock_user)

    with patch("app.api.v1.auth.User", MockUser), \
         patch("app.api.v1.auth.verify_password", return_value=True):
        payload = UserLogin(email="test@test.com", password="correct")
        with pytest.raises(HTTPException) as exc_info:
            await login(_mock_request(), payload)

    assert exc_info.value.status_code == 403
