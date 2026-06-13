"""Unit tests for scan_service — campaign scan triggering."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models.campaign import CampaignStatus
from app.services.scan_service import trigger_campaign_scan


# ---------------------------------------------------------------------------
# trigger_campaign_scan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_scan_campaign_not_found():
    """Return 404 when the campaign does not exist."""
    with patch(
        "app.models.campaign.Campaign.get", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await trigger_campaign_scan("nonexistent-id", "user@test.com")

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_trigger_scan_campaign_running(mock_campaign_pending):
    """Return 409 when the campaign status is not startable (RUNNING)."""
    mock_campaign_pending.status = CampaignStatus.RUNNING.value

    with patch(
        "app.models.campaign.Campaign.get", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = mock_campaign_pending

        with pytest.raises(HTTPException) as exc_info:
            await trigger_campaign_scan("campaign-abc123", "user@test.com")

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_trigger_scan_success(mock_campaign_pending):
    """Dispatch the Celery task when the campaign is in a valid state."""
    mock_campaign_pending.status = CampaignStatus.PENDING.value

    with patch(
        "app.models.campaign.Campaign.get", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = mock_campaign_pending

        result = await trigger_campaign_scan("campaign-abc123", "user@test.com")

    assert result["status"] == "accepted"
    assert result["campaign_id"] == "campaign-abc123"
    assert "task_id" in result
    assert result["task_id"] == "celery-scan-task-001"


@pytest.mark.asyncio
async def test_trigger_scan_failed_status_is_startable(mock_campaign_pending):
    """A FAILED campaign should also be startable (status is valid)."""
    mock_campaign_pending.status = CampaignStatus.FAILED.value

    with patch(
        "app.models.campaign.Campaign.get", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = mock_campaign_pending

        result = await trigger_campaign_scan("campaign-abc123", "user@test.com")

    assert result["status"] == "accepted"
