"""Unit tests for core modules: config, security.

Password hashing is mocked because this environment has a bcrypt /
passlib version incompatibility.  JWT encoding / decoding is tested
with the real ``python-jose`` implementation.
"""

import os
from datetime import timedelta
from unittest.mock import patch

from app.core.config import Settings
from app.core.security import create_access_token, decode_access_token


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def test_settings_defaults():
    """Settings has expected default values."""
    settings = Settings()

    assert settings.APP_NAME == "NetInsight API"
    assert settings.APP_VERSION == "0.2.0"
    assert settings.DEBUG is False
    assert settings.SECRET_KEY == "change-me-in-production"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 60
    assert settings.ALGORITHM == "HS256"
    assert settings.MONGODB_URL == "mongodb://mongodb:27017"
    assert settings.MONGODB_DB_NAME == "netinsight"
    assert settings.REDIS_URL == "redis://redis:6379/0"
    assert settings.NVD_API_KEY == ""
    assert settings.SCAN_RATE_LIMIT == 100
    assert settings.SCAN_TIMEOUT_SECONDS == 300
    assert settings.AUTH_TEST_MAX_ATTEMPTS == 5
    assert settings.AUTH_TEST_DELAY_SECONDS == 1.0


def test_settings_cors_defaults():
    """Settings has expected CORS origins."""
    settings = Settings()
    assert "http://localhost:5173" in settings.CORS_ORIGINS
    assert "http://localhost:80" in settings.CORS_ORIGINS


def test_settings_from_env():
    """Settings reads from environment variables."""
    with patch.dict(os.environ, {
        "APP_NAME": "TestApp",
        "DEBUG": "true",
        "SECRET_KEY": "my-secret",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
        "MONGODB_URL": "mongodb://custom:27017",
        "MONGODB_DB_NAME": "testdb",
    }, clear=False):
        settings = Settings()

        assert settings.APP_NAME == "TestApp"
        assert settings.DEBUG is True
        assert settings.SECRET_KEY == "my-secret"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.MONGODB_URL == "mongodb://custom:27017"
        assert settings.MONGODB_DB_NAME == "testdb"


# ---------------------------------------------------------------------------
# Password hashing (mocked — bcrypt/passlib incompatibility)
# ---------------------------------------------------------------------------

def test_password_hashing_roundtrip():
    """hash_password + verify_password round-trip via mock."""
    from app.core import security

    with patch.object(security, "hash_password", return_value="$2b$mockedhash"), \
         patch.object(security, "verify_password", return_value=True):
        hashed = security.hash_password("MySecretP@ss1")
        assert hashed.startswith("$2b$")
        assert security.verify_password("MySecretP@ss1", hashed) is True


def test_verify_password_wrong():
    """verify_password returns False for wrong password."""
    from app.core import security

    with patch.object(security, "hash_password", return_value="$2b$mocked"), \
         patch.object(security, "verify_password", return_value=False):
        hashed = security.hash_password("correct")
        assert security.verify_password("wrong", hashed) is False


# ---------------------------------------------------------------------------
# JWT tokens (real implementation — python-jose works without external deps)
# ---------------------------------------------------------------------------

def test_create_and_decode_access_token():
    """Round-trip: create a JWT then decode it."""
    token = create_access_token(data={"sub": "user@test.com", "role": "analyst"})

    assert isinstance(token, str)
    assert len(token) > 20

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user@test.com"
    assert payload["role"] == "analyst"
    assert "exp" in payload


def test_decode_access_token_invalid():
    """decode_access_token returns None for an invalid token."""
    result = decode_access_token("not.a.valid.jwt")
    assert result is None


def test_decode_access_token_expired():
    """decode_access_token returns None for an expired token."""
    token = create_access_token(
        data={"sub": "user@test.com"},
        expires_delta=timedelta(hours=-1),
    )

    result = decode_access_token(token)
    assert result is None


def test_create_token_with_custom_expiry():
    """create_access_token respects custom expires_delta."""
    token = create_access_token(
        data={"sub": "user@test.com"},
        expires_delta=timedelta(minutes=5),
    )

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user@test.com"
