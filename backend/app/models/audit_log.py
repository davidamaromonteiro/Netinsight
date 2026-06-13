"""AuditLog model – tracks all user actions for auditability."""

from datetime import datetime, timezone

from beanie import Document
from pydantic import Field


class AuditLog(Document):
    """An auditable action performed by a user on the platform."""

    user_email: str
    action: str  # e.g. "scan_created", "scan_triggered", "user_created"
    resource_type: str = ""  # e.g. "sqlmap_scan", "user", "campaign"
    resource_id: str = ""
    details: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "audit_logs"
        use_state_management = True
