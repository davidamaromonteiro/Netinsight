"""Service model – identified service on a port."""

from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class Service(Document):
    """A service identified on a given port."""

    host_id: Indexed(str)
    port_id: Indexed(str)
    name: str  # e.g. ssh, http, smb
    protocol: str = "tcp"
    version: Optional[str] = None
    product: Optional[str] = None
    extra_info: Optional[str] = None
    identified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "services"
        use_state_management = True

    def __repr__(self) -> str:
        return f"<Service {self.name} v{self.version}>"
