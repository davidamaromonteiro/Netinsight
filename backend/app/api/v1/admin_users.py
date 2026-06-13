"""Admin user management endpoints (admin-only)."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_admin, require_auth
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.audit_service import log_action

router = APIRouter(prefix="/admin/users", tags=["Admin / Users"])


@router.get("/", response_model=list[UserResponse])
async def list_users(
    role_filter: Optional[str] = Query(None, alias="role"),
    admin: User = Depends(require_admin),
):
    """List all users (admin only)."""
    query = {}
    if role_filter:
        query["role"] = role_filter
    users = await User.find(query).sort(-User.created_at).to_list()
    return [_user_to_response(u) for u in users]


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    email: str,
    password: str,
    full_name: Optional[str] = None,
    role: str = "analyst",
    admin: User = Depends(require_admin),
):
    """Create a new user (admin only)."""
    if role not in ("admin", "analyst", "viewer"):
        raise HTTPException(status_code=422, detail="Invalid role")

    existing = await User.find_one(User.email == email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
    )
    await user.insert()
    log_action(admin.email, "user_created", "user", str(user.id), {"email": email, "role": role})
    return _user_to_response(user)


@router.put("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    role: str,
    admin: User = Depends(require_admin),
):
    """Update a user's role (admin only)."""
    if role not in ("admin", "analyst", "viewer"):
        raise HTTPException(status_code=422, detail="Invalid role")

    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = role
    user.updated_at = datetime.now(timezone.utc)
    await user.save()
    log_action(admin.email, "user_role_changed", "user", user_id, {"role": role, "target": user.email})
    return _user_to_response(user)


@router.put("/{user_id}/toggle-active", response_model=UserResponse)
async def toggle_user_active(
    user_id: str,
    admin: User = Depends(require_admin),
):
    """Enable or disable a user account (admin only)."""
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if str(user.id) == str(admin.id):
        raise HTTPException(status_code=400, detail="Cannot disable your own account")

    user.is_active = not user.is_active
    user.updated_at = datetime.now(timezone.utc)
    await user.save()
    log_action(admin.email, "user_toggled", "user", user_id, {"active": user.is_active, "target": user.email})
    return _user_to_response(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
):
    """Delete a user (admin only)."""
    user = await User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if str(user.id) == str(admin.id):
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    await user.delete()
    log_action(admin.email, "user_deleted", "user", user_id, {"target": user.email})
    return None


def _user_to_response(u: User) -> UserResponse:
    return UserResponse(
        id=str(u.id),
        email=u.email,
        full_name=u.full_name,
        role=u.role,
        is_active=u.is_active,
        created_at=u.created_at,
    )
