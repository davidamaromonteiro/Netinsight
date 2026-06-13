"""Report model – generated analysis reports."""

from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class Report(Document):
    """A generated report for a campaign."""

    campaign_id: Indexed(str)
    title: str
    format: str = "pdf"  # pdf, csv, json
    file_path: Optional[str] = None
    size_bytes: Optional[int] = None
    summary: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "reports"
        use_state_management = True

    def __repr__(self) -> str:
        return f"<Report {self.title} .{self.format}>"
