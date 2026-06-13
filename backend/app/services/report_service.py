"""
Report generation service.
Wraps Celery task dispatching for PDF report generation.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import HTTPException, status

from app.models.campaign import Campaign, CampaignStatus
from app.models.report import Report

logger = logging.getLogger(__name__)


async def trigger_report_generation(campaign_id: str, user_email: str) -> dict:
    """Validate and dispatch a PDF report generation via Celery.

    Args:
        campaign_id: The ID of the campaign to generate a report for.
        user_email: The email of the authenticated user triggering the report.

    Returns:
        A dict with status, task_id, and campaign_id.

    Raises:
        HTTPException: 404 if the campaign does not exist,
                       409 if the campaign is not completed.
    """
    campaign = await Campaign.get(campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found",
        )

    if campaign.status != CampaignStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign must be completed to generate a report",
        )

    # Lazy import to avoid circular imports with Celery
    from app.tasks.reports import generate_campaign_report

    task = generate_campaign_report.delay(campaign_id)

    logger.info(
        "Report generation triggered by %s: campaign_id=%s task_id=%s",
        user_email,
        campaign_id,
        task.id,
    )

    return {
        "status": "accepted",
        "task_id": task.id,
        "campaign_id": campaign_id,
    }


async def get_campaign_report(campaign_id: str) -> Optional[dict]:
    """Retrieve the latest report for a given campaign.

    Args:
        campaign_id: The ID of the campaign.

    Returns:
        A dict with report information, or None if no report exists.
    """
    report = await Report.find_one(
        Report.campaign_id == campaign_id,
        sort=[("created_at", -1)],
    )
    if not report:
        return None

    return {
        "id": str(report.id),
        "campaign_id": report.campaign_id,
        "title": report.title,
        "format": report.format,
        "size_bytes": report.size_bytes,
        "summary": report.summary,
        "created_by": report.created_by,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


async def get_report_filepath(report_id: str) -> Optional[str]:
    """Retrieve the absolute file path for a generated report PDF.

    Args:
        report_id: The ID of the Report document.

    Returns:
        The absolute file path to the PDF, or None if not found.
    """
    report = await Report.get(report_id)
    if not report:
        return None

    if not report.file_path or not os.path.isfile(report.file_path):
        return None

    return os.path.abspath(report.file_path)
