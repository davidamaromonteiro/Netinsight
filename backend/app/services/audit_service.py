"""Audit logging helper – fire-and-forget action recording."""

import asyncio
import logging

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def log_action(
    user_email: str,
    action: str,
    resource_type: str = "",
    resource_id: str = "",
    details: dict | None = None,
) -> None:
    """Log an auditable action asynchronously (fire-and-forget)."""
    asyncio.create_task(_log_async(user_email, action, resource_type, resource_id, details))


async def _log_async(
    user_email: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: dict | None,
) -> None:
    try:
        log = AuditLog(
            user_email=user_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
        )
        await log.insert()
    except Exception as e:
        logger.warning("Failed to write audit log: %s", e)
