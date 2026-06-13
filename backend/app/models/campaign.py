"""Campaign model – represents a scan campaign."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from beanie import Document
from pydantic import Field


class CampaignStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Campaign(Document):
    """A scan campaign grouping targets and results."""

    name: str
    description: Optional[str] = None
    targets: list[str] = Field(default_factory=list)  # IPs, CIDRs, hostnames
    status: CampaignStatus = CampaignStatus.PENDING
    created_by: Optional[str] = None  # user email
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    scan_params: dict = Field(default_factory=dict)  # nmap options, etc.

    class Settings:
        name = "campaigns"
        use_state_management = True

    def __repr__(self) -> str:
        return f"<Campaign {self.name} [{self.status.value}]>"
