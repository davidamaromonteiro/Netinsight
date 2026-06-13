"""Pydantic schemas for Host."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class HostResponse(BaseModel):
    id: str
    ip: str
    hostname: Optional[str] = None
    mac_address: Optional[str] = None
    os: Optional[str] = None
    os_accuracy: Optional[int] = None
    status: str
    campaign_id: str
    first_seen: datetime
    last_seen: datetime


class HostDetail(HostResponse):
    """Host with open ports and services count."""
    port_count: int = 0
    vuln_count: int = 0
