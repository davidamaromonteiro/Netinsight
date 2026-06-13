"""Pydantic schemas for Port."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PortResponse(BaseModel):
    id: str
    host_id: str
    port: int
    protocol: str
    state: str
    service: Optional[str] = None
    version: Optional[str] = None
    extra_info: Optional[str] = None
    discovered_at: datetime
