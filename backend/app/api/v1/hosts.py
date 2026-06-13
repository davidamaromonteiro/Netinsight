"""Host endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_auth
from app.api.v1.vulnerabilities import _vuln_to_response
from app.models.host import Host
from app.models.port import Port
from app.models.user import User
from app.models.vulnerability import Vulnerability
from app.schemas.host import HostDetail
from app.schemas.port import PortResponse
from app.schemas.vulnerability import VulnerabilityResponse

router = APIRouter(prefix="/hosts", tags=["Hosts"], redirect_slashes=False)


@router.get("/", response_model=list[HostDetail])
async def list_hosts(
    campaign_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user: User = Depends(require_auth),
):
    """List hosts, optionally filtered by campaign or status."""
    query = {}
    if campaign_id:
        query["campaign_id"] = campaign_id
    if status:
        query["status"] = status

    hosts = await Host.find(query).sort(+Host.ip).to_list()
    result = []
    for h in hosts:
        port_count = await Port.find(
            Port.host_id == str(h.id), Port.state == "open"
        ).count()
        vuln_count = await Vulnerability.find(
            Vulnerability.host_id == str(h.id)
        ).count()
        result.append(
            HostDetail(
                id=str(h.id),
                ip=h.ip,
                hostname=h.hostname,
                mac_address=h.mac_address,
                os=h.os,
                os_accuracy=h.os_accuracy,
                status=h.status,
                campaign_id=h.campaign_id,
                first_seen=h.first_seen,
                last_seen=h.last_seen,
                port_count=port_count,
                vuln_count=vuln_count,
            )
        )
    return result


@router.get("/{host_id}", response_model=HostDetail)
async def get_host(
    host_id: str,
    user: User = Depends(require_auth),
):
    """Get a single host by ID with port/vuln counts."""
    host = await Host.get(host_id)
    if not host:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    port_count = await Port.find(
        Port.host_id == host_id, Port.state == "open"
    ).count()
    vuln_count = await Vulnerability.find(Vulnerability.host_id == host_id).count()
    return HostDetail(
        id=str(host.id),
        ip=host.ip,
        hostname=host.hostname,
        mac_address=host.mac_address,
        os=host.os,
        os_accuracy=host.os_accuracy,
        status=host.status,
        campaign_id=host.campaign_id,
        first_seen=host.first_seen,
        last_seen=host.last_seen,
        port_count=port_count,
        vuln_count=vuln_count,
    )


@router.get("/{host_id}/ports", response_model=list[PortResponse])
async def get_host_ports(
    host_id: str,
    state: Optional[str] = Query("open"),
    user: User = Depends(require_auth),
):
    """List ports for a given host, filtered by state (default: open)."""
    host = await Host.get(host_id)
    if not host:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    query = {"host_id": host_id}
    if state:
        query["state"] = state

    ports = await Port.find(query).sort(+Port.port).to_list()
    return [
        PortResponse(
            id=str(p.id),
            host_id=p.host_id,
            port=p.port,
            protocol=p.protocol,
            state=p.state,
            service=p.service,
            version=p.version,
            extra_info=p.extra_info,
            discovered_at=p.discovered_at,
        )
        for p in ports
    ]


@router.get("/{host_id}/vulnerabilities", response_model=list[VulnerabilityResponse])
async def get_host_vulnerabilities(
    host_id: str,
    user: User = Depends(require_auth),
):
    """List vulnerabilities found on a specific host."""
    host = await Host.get(host_id)
    if not host:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host not found")

    vulns = await Vulnerability.find(
        Vulnerability.host_id == host_id
    ).sort(-Vulnerability.cvss_score).to_list()

    return [_vuln_to_response(v) for v in vulns]


@router.post("/{host_id}/enrich", status_code=status.HTTP_202_ACCEPTED)
async def enrich_host(
    host_id: str,
    user: User = Depends(require_auth),
):
    """Trigger CVE + MITRE enrichment for a host."""
    host = await Host.get(host_id)
    if not host:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    result = {"host_id": host_id, "mitre": None, "nvd": None}

    # MITRE mapping (fast, uses static data)
    try:
        from app.services.mitre_service import map_host_ports_to_mitre
        result["mitre"] = await map_host_ports_to_mitre(host_id)
    except Exception as e:
        result["mitre"] = {"error": str(e)}

    # NVD enrichment (slower, calls external API)
    try:
        from app.services.nvd_service import enrich_host_vulnerabilities
        result["nvd"] = await enrich_host_vulnerabilities(host_id)
    except Exception as e:
        result["nvd"] = {"error": str(e)}

    return result
