"""Host model – discovered network host."""

from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class Host(Document):
    """A discovered host on the network."""

    ip: str
    hostname: Optional[str] = None
    mac_address: Optional[str] = None
    os: Optional[str] = None  # detected operating system
    os_accuracy: Optional[int] = None
    status: str = "unknown"  # up / down / unknown
    campaign_id: Indexed(str)
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "hosts"
        use_state_management = True

    def __repr__(self) -> str:
        return f"<Host {self.ip}>"
