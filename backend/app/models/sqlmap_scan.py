"""SqlmapScan model – represents a SQL injection scan."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from beanie import Document
from pydantic import Field


class SqlmapScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SqlmapScan(Document):
    """A SQL injection scan using sqlmap against a target URL."""

    name: str
    description: Optional[str] = None
    target_url: str
    status: SqlmapScanStatus = SqlmapScanStatus.PENDING
    sqlmap_params: dict = Field(default_factory=dict)
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_summary: Optional[dict] = None
    vulnerabilities_found: int = 0
    raw_output: Optional[str] = None

    class Settings:
        name = "sqlmap_scans"
        use_state_management = True

    def __repr__(self) -> str:
        return f"<SqlmapScan {self.name} [{self.status.value}]>"
