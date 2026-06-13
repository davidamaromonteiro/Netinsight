"""Shared pytest fixtures for NetInsight unit tests."""

import sys
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Beanie mock — allow Document instantiation without MongoDB
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_beanie_document():
    """Allow Beanie Documents to be instantiated without a live MongoDB.

    Without this fixture every ``Campaign(...)`` / ``Host(...)`` / etc. call
    raises ``CollectionWasNotInitialized`` because ``Document.__init__``
    eagerly accesses the PyMongo collection.
    """
    from beanie.odm.documents import Document

    _original = Document.get_pymongo_collection

    def _fake_collection(self):
        return MagicMock()

    Document.get_pymongo_collection = _fake_collection
    yield
    Document.get_pymongo_collection = _original


# ---------------------------------------------------------------------------
# Celery task mocks — inject fake modules so lazy imports succeed
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_celery_modules():
    """Replace Celery task modules with mocks so that ``from app.tasks.X``
    imports inside service functions resolve without a real Redis/Celery
    installation."""
    scans = MagicMock()
    scans.run_campaign_scan = MagicMock()
    scans.run_campaign_scan.delay.return_value = MagicMock(id="celery-scan-task-001")

    reports = MagicMock()
    reports.generate_campaign_report = MagicMock()
    reports.generate_campaign_report.delay.return_value = MagicMock(
        id="celery-report-task-001"
    )

    sys.modules["app.tasks.scans"] = scans
    sys.modules["app.tasks.reports"] = reports
    yield
    # Clean up so that other test suites (e.g. integration) start fresh
    sys.modules.pop("app.tasks.scans", None)
    sys.modules.pop("app.tasks.reports", None)


# ---------------------------------------------------------------------------
# Reusable model fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_campaign_pending():
    """A mock Campaign document in PENDING state."""
    campaign = MagicMock()
    campaign.id = "campaign-abc123"
    campaign.name = "Test Campaign"
    campaign.description = "A test campaign"
    campaign.targets = ["10.0.0.1"]
    campaign.status = "pending"
    campaign.created_by = "tester@netinsight.io"
    return campaign


@pytest.fixture
def mock_campaign_completed():
    """A mock Campaign document in COMPLETED state."""
    campaign = MagicMock()
    campaign.id = "campaign-xyz789"
    campaign.name = "Completed Campaign"
    campaign.description = "A completed campaign"
    campaign.targets = ["10.0.0.2"]
    campaign.status = "completed"
    campaign.created_by = "tester@netinsight.io"
    return campaign


@pytest.fixture
def mock_report_doc():
    """A mock Report document with all fields populated."""
    report = MagicMock()
    report.id = "report-001"
    report.campaign_id = "campaign-xyz789"
    report.title = "Security Audit Report"
    report.format = "pdf"
    report.file_path = "/tmp/report-001.pdf"
    report.size_bytes = 42_000
    report.summary = "All systems nominal."
    report.created_by = "tester@netinsight.io"
    report.created_at = MagicMock()
    report.created_at.isoformat.return_value = "2026-01-15T10:30:00+00:00"
    return report
