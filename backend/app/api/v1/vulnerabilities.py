"""Vulnerability listing endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_auth
from app.models.user import User
from app.models.vulnerability import Vulnerability
from app.schemas.vulnerability import VulnerabilityResponse

router = APIRouter(prefix="/vulnerabilities", tags=["Vulnerabilities"], redirect_slashes=False)


def _vuln_to_response(v: Vulnerability) -> VulnerabilityResponse:
    """Map a Vulnerability document to its response schema."""
    return VulnerabilityResponse(
        id=str(v.id),
        host_id=v.host_id,
        service_id=v.service_id,
        cve_id=v.cve_id,
        cvss_score=v.cvss_score,
        severity=v.severity,
        description=v.description,
        vector=v.vector,
        published_date=v.published_date,
        discovered_at=v.discovered_at,
    )


@router.get("/", response_model=list[VulnerabilityResponse])
async def list_vulnerabilities(
    host_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None, description="Filter by severity: critical, high, medium, low"),
    user: User = Depends(require_auth),
):
    """List all vulnerabilities, with optional host and severity filters.

    Results are sorted by CVSS score descending (most critical first).
    """
    query = {}
    if host_id:
        query["host_id"] = host_id
    if severity:
        query["severity"] = severity.lower()

    vulns = await Vulnerability.find(query).sort(-Vulnerability.cvss_score).to_list()
    return [_vuln_to_response(v) for v in vulns]


@router.get("/{vulnerability_id}", response_model=VulnerabilityResponse)
async def get_vulnerability(
    vulnerability_id: str,
    user: User = Depends(require_auth),
):
    """Get a single vulnerability by ID."""
    vuln = await Vulnerability.get(vulnerability_id)
    if not vuln:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vulnerability not found",
        )
    return _vuln_to_response(vuln)
