"""Nikto web server scan model."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class NiktoScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class NiktoScan(Document):
    """A Nikto web server vulnerability scan."""

    name: str
    description: Optional[str] = None
    target_url: str
    target_host: str  # IP or hostname
    target_port: int = 80
    use_ssl: bool = False
    status: NiktoScanStatus = NiktoScanStatus.PENDING
    nikto_params: dict = Field(default_factory=dict)
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    vulnerabilities_found: int = 0
    result_summary: Optional[dict] = None
    raw_output: Optional[str] = None

    class Settings:
        name = "nikto_scans"
        use_state_management = True
