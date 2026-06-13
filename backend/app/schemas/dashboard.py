"""Pydantic schemas for the Dashboard."""

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_campaigns: int = 0
    active_campaigns: int = 0
    total_hosts: int = 0
    total_ports: int = 0
    total_services: int = 0
    total_vulnerabilities: int = 0
    vulnerabilities_by_severity: dict = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "none": 0,
    }
    total_auth_tests: int = 0
    auth_test_success_rate: float = 0.0
