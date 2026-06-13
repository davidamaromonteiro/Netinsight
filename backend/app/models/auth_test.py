"""Auth test model – results of authorised authentication attempts."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class AuthTestResult(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class AuthTest(Document):
    """An authentication test against a discovered service."""

    campaign_id: Indexed(str)
    host_id: Indexed(str)
    port_id: str
    service_name: str  # ssh, ftp, smb, etc.
    username: str
    result: AuthTestResult = AuthTestResult.FAILED
    output: Optional[str] = None
    duration_seconds: Optional[float] = None
    tested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "auth_tests"
        use_state_management = True

    def __repr__(self) -> str:
        return f"<AuthTest {self.service_name}@{self.username} [{self.result.value}]>"
