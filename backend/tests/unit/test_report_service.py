"""Unit tests for report_service — report generation and retrieval."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.campaign import CampaignStatus
from app.services.report_service import (
    get_campaign_report,
    get_report_filepath,
    trigger_report_generation,
)


# ---------------------------------------------------------------------------
# trigger_report_generation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_report_campaign_not_found():
    """Return 404 when the campaign does not exist."""
    with patch(
        "app.models.campaign.Campaign.get", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await trigger_report_generation("nonexistent-id", "user@test.com")

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_trigger_report_campaign_not_completed(mock_campaign_pending):
    """Return 409 when the campaign status is not COMPLETED."""
    mock_campaign_pending.status = CampaignStatus.PENDING.value

    with patch(
        "app.models.campaign.Campaign.get", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = mock_campaign_pending

        with pytest.raises(HTTPException) as exc_info:
            await trigger_report_generation("campaign-abc123", "user@test.com")

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_trigger_report_success(mock_campaign_completed):
    """Dispatch the Celery report task when the campaign is COMPLETED."""
    with patch(
        "app.models.campaign.Campaign.get", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = mock_campaign_completed

        result = await trigger_report_generation(
            "campaign-xyz789", "user@test.com"
        )

    assert result["status"] == "accepted"
    assert result["campaign_id"] == "campaign-xyz789"
    assert "task_id" in result
    assert result["task_id"] == "celery-report-task-001"


# ---------------------------------------------------------------------------
# get_campaign_report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_campaign_report_not_found():
    """Return None when no report exists for the campaign."""
    mock_report_cls = MagicMock()
    mock_report_cls.find_one = AsyncMock(return_value=None)

    with patch("app.services.report_service.Report", mock_report_cls):
        result = await get_campaign_report("campaign-no-report")

    assert result is None


@pytest.mark.asyncio
async def test_get_campaign_report_success(mock_report_doc):
    """Return a correctly formatted dict when a report exists."""
    mock_report_cls = MagicMock()
    mock_report_cls.find_one = AsyncMock(return_value=mock_report_doc)

    with patch("app.services.report_service.Report", mock_report_cls):
        result = await get_campaign_report("campaign-xyz789")

    assert result is not None
    assert result["id"] == "report-001"
    assert result["campaign_id"] == "campaign-xyz789"
    assert result["title"] == "Security Audit Report"
    assert result["format"] == "pdf"
    assert result["size_bytes"] == 42_000
    assert result["summary"] == "All systems nominal."
    assert result["created_by"] == "tester@netinsight.io"
    assert result["created_at"] == "2026-01-15T10:30:00+00:00"


# ---------------------------------------------------------------------------
# get_report_filepath
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_report_filepath_not_found():
    """Return None when the Report document does not exist."""
    with patch(
        "app.models.report.Report.get", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = None

        result = await get_report_filepath("report-999")

    assert result is None


@pytest.mark.asyncio
async def test_get_report_filepath_missing_file(mock_report_doc):
    """Return None when the document exists but the file is missing."""
    mock_report_doc.file_path = "/tmp/no-such-file.pdf"

    with patch(
        "app.models.report.Report.get", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = mock_report_doc

        with patch("os.path.isfile", return_value=False):
            result = await get_report_filepath("report-001")

    assert result is None


@pytest.mark.asyncio
async def test_get_report_filepath_success(mock_report_doc):
    """Return the absolute file path when the report file exists."""
    mock_report_doc.file_path = "/tmp/report-001.pdf"

    with patch(
        "app.models.report.Report.get", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = mock_report_doc

        with patch("os.path.isfile", return_value=True):
            result = await get_report_filepath("report-001")

    assert result == os.path.abspath("/tmp/report-001.pdf")
    assert result is not None
