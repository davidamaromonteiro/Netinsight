"""Audit log query endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import require_auth
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/")
async def list_logs(
    action: Optional[str] = Query(None),
    user_email: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    current_user: User = Depends(require_auth),
):
    """List audit logs, optionally filtered by action or user."""
    query = {}
    if action:
        query["action"] = action
    if user_email:
        query["user_email"] = user_email

    logs = await AuditLog.find(query).sort(-AuditLog.created_at).limit(limit).to_list()
    return [
        {
            "id": str(l.id),
            "user_email": l.user_email,
            "action": l.action,
            "resource_type": l.resource_type,
            "resource_id": l.resource_id,
            "details": l.details,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]
