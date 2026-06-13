"""Pydantic schemas for Banner."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class BannerResponse(BaseModel):
    id: str
    host_id: str
    port_id: str
    service_name: str
    raw_banner: str
    parsed_info: Optional[dict] = None
    grabbed_at: datetime
