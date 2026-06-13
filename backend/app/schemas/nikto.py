"""Pydantic schemas for NiktoScan."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NiktoScanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    target_url: str = Field(min_length=1, max_length=2048)
    target_host: str
    target_port: int = 80
    use_ssl: bool = False
    nikto_params: dict = Field(default_factory=dict)


class NiktoScanResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    target_url: str
    target_host: str
    target_port: int
    use_ssl: bool
    status: str
    nikto_params: dict
    created_by: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    vulnerabilities_found: int
    result_summary: Optional[dict] = None
    raw_output: Optional[str] = None
