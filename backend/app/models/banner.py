"""Banner model – service banner information."""

from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class Banner(Document):
    """A service banner grabbed from an open port."""

    host_id: Indexed(str)
    port_id: Indexed(str)
    service_name: str
    raw_banner: str
    parsed_info: Optional[dict] = None
    grabbed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "banners"
        use_state_management = True

    def __repr__(self) -> str:
        return f"<Banner {self.service_name}>"
