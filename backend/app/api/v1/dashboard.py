"""Dashboard endpoints – aggregate statistics."""

from fastapi import APIRouter, Depends

from app.api.deps import require_auth
from app.models.auth_test import AuthTest, AuthTestResult
from app.models.campaign import Campaign, CampaignStatus
from app.models.host import Host
from app.models.port import Port
from app.models.service import Service
from app.models.user import User
from app.models.vulnerability import Vulnerability
from app.schemas.dashboard import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(user: User = Depends(require_auth)):
    """Return aggregate statistics for the dashboard."""
    total_campaigns = await Campaign.find().count()
    active_campaigns = await Campaign.find(
        Campaign.status == CampaignStatus.RUNNING
    ).count()
    total_hosts = await Host.find().count()
    total_ports = await Port.find(Port.state == "open").count()
    total_services = await Service.find().count()
    total_vulnerabilities = await Vulnerability.find().count()

    # Vulnerabilities by severity
    vulns = await Vulnerability.find().to_list()
    severity_dist = {"critical": 0, "high": 0, "medium": 0, "low": 0, "none": 0}
    for v in vulns:
        sev = (v.severity or "none").lower()
        if sev in severity_dist:
            severity_dist[sev] += 1

    # Auth test stats
    total_auth_tests = await AuthTest.find().count()
    success_count = await AuthTest.find(
        AuthTest.result == AuthTestResult.SUCCESS
    ).count()
    success_rate = (success_count / total_auth_tests * 100) if total_auth_tests > 0 else 0.0

    return DashboardStats(
        total_campaigns=total_campaigns,
        active_campaigns=active_campaigns,
        total_hosts=total_hosts,
        total_ports=total_ports,
        total_services=total_services,
        total_vulnerabilities=total_vulnerabilities,
        vulnerabilities_by_severity=severity_dist,
        total_auth_tests=total_auth_tests,
        auth_test_success_rate=round(success_rate, 1),
    )
