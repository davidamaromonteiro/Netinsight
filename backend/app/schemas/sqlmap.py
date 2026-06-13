"""Pydantic schemas for SqlmapScan."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SqlmapScanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    target_url: str = Field(min_length=1, max_length=2048)
    sqlmap_params: dict = Field(default_factory=dict)


class SqlmapScanResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    target_url: str
    status: str
    sqlmap_params: dict
    created_by: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_summary: Optional[dict] = None
    vulnerabilities_found: int
    raw_output: Optional[str] = None
