"""Campaign management endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_auth
from app.models.auth_test import AuthTest
from app.models.campaign import Campaign
from app.models.host import Host
from app.models.user import User
from app.models.vulnerability import Vulnerability
from app.schemas.campaign import CampaignCreate, CampaignResponse, CampaignSummary

router = APIRouter(prefix="/campaigns", tags=["Campaigns"], redirect_slashes=False)


@router.post("/", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    user: User = Depends(require_auth),
):
    """Create a new scan campaign."""
    campaign = Campaign(
        name=payload.name,
        description=payload.description,
        targets=payload.targets,
        scan_params=payload.scan_params,
        created_by=user.email,
    )
    await campaign.insert()
    return _campaign_to_response(campaign)


@router.get("/", response_model=list[CampaignSummary])
async def list_campaigns(
    status_filter: Optional[str] = Query(None, alias="status"),
    user: User = Depends(require_auth),
):
    """List all campaigns, optionally filtered by status."""
    query = {}
    if status_filter:
        query["status"] = status_filter
    campaigns = await Campaign.find(query).sort(-Campaign.created_at).to_list()

    result = []
    for c in campaigns:
        host_count = await Host.find(Host.campaign_id == str(c.id)).count()
        vuln_count = await Vulnerability.find(
            Vulnerability.campaign_id == str(c.id)
        ).count()
        result.append(
            CampaignSummary(
                id=str(c.id),
                name=c.name,
                status=c.status.value,
                target_count=len(c.targets),
                host_count=host_count,
                vuln_count=vuln_count,
                created_at=c.created_at,
            )
        )
    return result


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    user: User = Depends(require_auth),
):
    """Get a single campaign by ID."""
    campaign = await Campaign.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _campaign_to_response(campaign)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: str,
    user: User = Depends(require_auth),
):
    """Delete a campaign and its associated data."""
    campaign = await Campaign.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Remove associated data
    await Host.find(Host.campaign_id == campaign_id).delete()
    await Vulnerability.find(Vulnerability.campaign_id == campaign_id).delete()
    await AuthTest.find(AuthTest.campaign_id == campaign_id).delete()
    await campaign.delete()
    return None


@router.post("/{campaign_id}/scan", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scan(
    campaign_id: str,
    user: User = Depends(require_auth),
):
    """Start a scan for the given campaign."""
    from app.services.scan_service import trigger_campaign_scan

    return await trigger_campaign_scan(campaign_id, user.email)


@router.post("/{campaign_id}/report", status_code=status.HTTP_202_ACCEPTED)
async def trigger_report(
    campaign_id: str,
    user: User = Depends(require_auth),
):
    """Generate a PDF report for the given campaign."""
    from app.services.report_service import trigger_report_generation

    return await trigger_report_generation(campaign_id, user.email)


@router.get("/{campaign_id}/report")
async def get_report_info(
    campaign_id: str,
    user: User = Depends(require_auth),
):
    """Get the latest report info for a campaign."""
    from app.services.report_service import get_campaign_report

    report = await get_campaign_report(campaign_id)
    if not report:
        raise HTTPException(status_code=404, detail="No report found for this campaign")
    return report


def _campaign_to_response(c: Campaign) -> CampaignResponse:
    return CampaignResponse(
        id=str(c.id),
        name=c.name,
        description=c.description,
        targets=c.targets,
        status=c.status.value,
        created_by=c.created_by,
        created_at=c.created_at,
        started_at=c.started_at,
        completed_at=c.completed_at,
    )
