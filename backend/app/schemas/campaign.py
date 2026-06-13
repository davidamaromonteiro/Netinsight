"""Pydantic schemas for Campaign."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    targets: list[str] = Field(min_length=1)
    scan_params: dict = Field(default_factory=dict)


class CampaignResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    targets: list[str]
    status: str
    created_by: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class CampaignSummary(BaseModel):
    """Lightweight campaign info for dashboard lists."""

    id: str
    name: str
    status: str
    target_count: int
    host_count: int
    vuln_count: int
    created_at: datetime
