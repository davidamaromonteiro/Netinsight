"""
Scan orchestration service.
Wraps Celery task dispatching with business validation.
"""

import logging

from fastapi import HTTPException, status

from app.models.campaign import Campaign, CampaignStatus

logger = logging.getLogger(__name__)


async def trigger_campaign_scan(campaign_id: str, user_email: str) -> dict:
    """Validate and dispatch a campaign scan via Celery.

    Args:
        campaign_id: The ID of the campaign to scan.
        user_email: The email of the authenticated user triggering the scan.

    Returns:
        A dict with status, task_id, and campaign_id.

    Raises:
        HTTPException: 404 if the campaign does not exist,
                       409 if the campaign is not in a startable state.
    """
    # Fetch the campaign
    campaign = await Campaign.get(campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )

    # Validate campaign status
    if campaign.status not in (CampaignStatus.PENDING, CampaignStatus.FAILED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign must be pending or failed to start a scan",
        )

    # Lazy import to avoid circular imports with Celery
    from app.tasks.scans import run_campaign_scan

    task = run_campaign_scan.delay(campaign_id)

    logger.info(
        "Campaign scan triggered by %s: campaign_id=%s task_id=%s",
        user_email,
        campaign_id,
        task.id,
    )

    return {
        "status": "accepted",
        "task_id": task.id,
        "campaign_id": campaign_id,
    }
