"""AppConfig model – application-level configuration stored in MongoDB."""

from datetime import datetime, timezone
from typing import Optional

from beanie import Document
from pydantic import Field


class AppConfig(Document):
    """Persistent application configuration."""

    key: str  # configuration key
    value: dict  # configuration value
    description: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: Optional[str] = None

    class Settings:
        name = "config"
        use_state_management = True

    def __repr__(self) -> str:
        return f"<AppConfig {self.key}>"
