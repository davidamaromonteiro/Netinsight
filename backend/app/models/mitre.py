"""MITRE ATT&CK technique model."""

from datetime import datetime, timezone
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class MitreTechnique(Document):
    """A MITRE ATT&CK technique mapped to a vulnerability or service."""

    vulnerability_id: Optional[Indexed(str)] = None
    service_id: Optional[Indexed(str)] = None
    technique_id: str  # e.g. T1190
    technique_name: str
    tactic: str  # e.g. Initial Access
    tactic_id: str  # e.g. TA0001
    description: Optional[str] = None
    url: Optional[str] = None
    mapped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "mitre_techniques"
        use_state_management = True

    def __repr__(self) -> str:
        return f"<MitreTechnique {self.technique_id} – {self.tactic}>"
