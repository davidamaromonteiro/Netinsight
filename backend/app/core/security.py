"""JWT authentication & password hashing utilities."""


from datetime import datetime, timedelta, timezone
from typing import Optional, cast

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain-text password against its bcrypt hash."""
    return cast(bool, pwd_context.verify(plain_password, hashed_password))


def hash_password(password: str) -> str:
    """Return the bcrypt hash of a password."""
    return cast(str, pwd_context.hash(password))


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return cast(str, jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM))


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token. Returns the payload or None."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return cast(dict, payload)
    except JWTError:
        return None
