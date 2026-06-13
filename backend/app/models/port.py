"""Port model – open/closed port on a host."""

from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class Port(Document):
    """A network port discovered on a host."""

    host_id: Indexed(str)
    port: int
    protocol: str = "tcp"  # tcp / udp
    state: str = "open"  # open / closed / filtered
    service: Optional[str] = None
    version: Optional[str] = None
    extra_info: Optional[str] = None
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "ports"
        use_state_management = True

    def __repr__(self) -> str:
        return f"<Port {self.port}/{self.protocol} ({self.state})>"
