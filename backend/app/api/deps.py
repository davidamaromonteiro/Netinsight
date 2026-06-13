"""FastAPI dependency injection utilities."""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.models.user import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """Extract and return the current authenticated user from the JWT token.

    Returns None if no token is provided (unauthenticated access).
    """
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None
    user = await User.find_one(User.email == payload.get("sub"))
    return user


async def require_admin(user: Optional[User] = Depends(get_current_user)) -> User:
    """Require an authenticated admin user."""
    if user is None or user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


async def require_auth(user: Optional[User] = Depends(get_current_user)) -> User:
    """Require any authenticated user."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


async def require_analyst(user: Optional[User] = Depends(get_current_user)) -> User:
    """Require admin or analyst role (can create/trigger/delete scans)."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    if user.role not in ("admin", "analyst"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analyst privileges required",
        )
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """Return the current user or None (no auth required)."""
    return await get_current_user(credentials)
