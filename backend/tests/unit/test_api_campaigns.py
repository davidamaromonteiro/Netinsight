"""Unit tests for campaign API endpoints.

Tests call the async router functions directly.  Because Beanie class
field access (``Campaign.created_at``, ``Host.campaign_id``, ...)
requires MongoDB initialisation, the full model classes are mocked.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.campaigns import (
    create_campaign,
    list_campaigns,
    get_campaign,
    delete_campaign,
)
from app.models.campaign import CampaignStatus
from app.schemas.campaign import CampaignCreate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_auth_user(email="tester@netinsight.io"):
    """Mock authenticated user for the ``user=Depends(require_auth)`` parameter."""
    user = MagicMock()
    user.email = email
    return user


def _mock_campaign_doc(campaign_id="camp-001", name="Test Campaign",
                        status=CampaignStatus.PENDING):
    """Mock a Campaign Beanie document instance."""
    c = MagicMock()
    c.id = campaign_id
    c.name = name
    c.description = "A test campaign"
    c.targets = ["10.0.0.1", "10.0.0.2"]
    c.status = status  # real CampaignStatus enum → .value works
    c.created_by = "tester@netinsight.io"
    c.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    c.started_at = None
    c.completed_at = None
    c.insert = AsyncMock()
    c.delete = AsyncMock()
    return c


def _make_chain(to_list=None, count=0):
    """Build a mock chain for ``.find().sort().to_list()`` / ``.count()``."""
    chain = MagicMock()
    chain.sort.return_value = chain
    chain.to_list = AsyncMock(return_value=to_list or [])
    chain.count = AsyncMock(return_value=count)
    chain.delete = AsyncMock()
    return chain


# ---------------------------------------------------------------------------
# POST /campaigns/
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_campaign():
    """POST /campaigns/ — 201, returns CampaignResponse."""
    mock_camp = _mock_campaign_doc()
    mock_user = _mock_auth_user()

    MockCampaign = MagicMock(name="Campaign")
    MockCampaign.return_value = mock_camp

    with patch("app.api.v1.campaigns.Campaign", MockCampaign):
        payload = CampaignCreate(name="Test Campaign", targets=["10.0.0.1", "10.0.0.2"])
        result = await create_campaign(payload=payload, user=mock_user)

    assert result.id == "camp-001"
    assert result.name == "Test Campaign"
    assert result.status == "pending"
    assert result.targets == ["10.0.0.1", "10.0.0.2"]
    assert result.created_by == "tester@netinsight.io"
    mock_camp.insert.assert_awaited_once()


# ---------------------------------------------------------------------------
# GET /campaigns/
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_campaigns():
    """GET /campaigns/ — 200, returns list of CampaignSummary."""
    mock_camp = _mock_campaign_doc()
    mock_user = _mock_auth_user()

    MockCampaign = MagicMock(name="Campaign")
    MockCampaign.find.return_value = _make_chain(to_list=[mock_camp])
    MockCampaign.created_at = MagicMock()  # used in sort expression

    MockHost = MagicMock(name="Host")
    MockHost.find.return_value = _make_chain(count=3)

    MockVuln = MagicMock(name="Vulnerability")
    MockVuln.find.return_value = _make_chain(count=2)
    MockVuln.campaign_id = MagicMock()  # for query expression

    with patch("app.api.v1.campaigns.Campaign", MockCampaign), \
         patch("app.api.v1.campaigns.Host", MockHost), \
         patch("app.api.v1.campaigns.Vulnerability", MockVuln):
        result = await list_campaigns(user=mock_user)

    assert len(result) == 1
    s = result[0]
    assert s.id == "camp-001"
    assert s.name == "Test Campaign"
    assert s.status == "pending"
    assert s.target_count == 2
    assert s.host_count == 3
    assert s.vuln_count == 2


@pytest.mark.asyncio
async def test_list_campaigns_with_status_filter():
    """GET /campaigns/?status=running — filters by status."""
    mock_camp = _mock_campaign_doc(status=CampaignStatus.RUNNING)
    mock_user = _mock_auth_user()

    MockCampaign = MagicMock(name="Campaign")
    MockCampaign.find.return_value = _make_chain(to_list=[mock_camp])
    MockCampaign.created_at = MagicMock()

    MockHost = MagicMock(name="Host")
    MockHost.find.return_value = _make_chain(count=0)

    MockVuln = MagicMock(name="Vulnerability")
    MockVuln.find.return_value = _make_chain(count=0)
    MockVuln.campaign_id = MagicMock()

    with patch("app.api.v1.campaigns.Campaign", MockCampaign), \
         patch("app.api.v1.campaigns.Host", MockHost), \
         patch("app.api.v1.campaigns.Vulnerability", MockVuln):
        result = await list_campaigns(status_filter="running", user=mock_user)

    assert len(result) == 1
    assert result[0].status == "running"


@pytest.mark.asyncio
async def test_list_campaigns_empty():
    """GET /campaigns/ — returns empty list when no campaigns exist."""
    mock_user = _mock_auth_user()

    MockCampaign = MagicMock(name="Campaign")
    MockCampaign.find.return_value = _make_chain(to_list=[])
    MockCampaign.created_at = MagicMock()

    with patch("app.api.v1.campaigns.Campaign", MockCampaign):
        result = await list_campaigns(user=mock_user)

    assert result == []


# ---------------------------------------------------------------------------
# GET /campaigns/{campaign_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_campaign_found():
    """GET /campaigns/{id} — 200 when campaign exists."""
    mock_camp = _mock_campaign_doc()
    mock_user = _mock_auth_user()

    MockCampaign = MagicMock(name="Campaign")
    MockCampaign.get = AsyncMock(return_value=mock_camp)

    with patch("app.api.v1.campaigns.Campaign", MockCampaign):
        result = await get_campaign(campaign_id="camp-001", user=mock_user)

    assert result.id == "camp-001"
    assert result.name == "Test Campaign"


@pytest.mark.asyncio
async def test_get_campaign_not_found():
    """GET /campaigns/{id} — 404 when campaign does not exist."""
    mock_user = _mock_auth_user()

    MockCampaign = MagicMock(name="Campaign")
    MockCampaign.get = AsyncMock(return_value=None)

    with patch("app.api.v1.campaigns.Campaign", MockCampaign):
        with pytest.raises(HTTPException) as exc_info:
            await get_campaign(campaign_id="nonexistent", user=mock_user)

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /campaigns/{campaign_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_campaign_success():
    """DELETE /campaigns/{id} — 204, deletes campaign + associated data."""
    mock_camp = _mock_campaign_doc()
    mock_user = _mock_auth_user()

    host_chain = _make_chain()
    vuln_chain = _make_chain()
    auth_chain = _make_chain()

    MockCampaign = MagicMock(name="Campaign")
    MockCampaign.get = AsyncMock(return_value=mock_camp)

    MockHost = MagicMock(name="Host")
    MockHost.find.return_value = host_chain
    MockHost.campaign_id = MagicMock()

    MockVuln = MagicMock(name="Vulnerability")
    MockVuln.find.return_value = vuln_chain
    MockVuln.campaign_id = MagicMock()

    MockAuthTest = MagicMock(name="AuthTest")
    MockAuthTest.find.return_value = auth_chain
    MockAuthTest.campaign_id = MagicMock()

    with patch("app.api.v1.campaigns.Campaign", MockCampaign), \
         patch("app.api.v1.campaigns.Host", MockHost), \
         patch("app.api.v1.campaigns.Vulnerability", MockVuln), \
         patch("app.api.v1.campaigns.AuthTest", MockAuthTest):
        result = await delete_campaign(campaign_id="camp-001", user=mock_user)

    assert result is None  # 204 No Content
    host_chain.delete.assert_awaited_once()
    vuln_chain.delete.assert_awaited_once()
    auth_chain.delete.assert_awaited_once()
    mock_camp.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_campaign_not_found():
    """DELETE /campaigns/{id} — 404 when campaign does not exist."""
    mock_user = _mock_auth_user()

    MockCampaign = MagicMock(name="Campaign")
    MockCampaign.get = AsyncMock(return_value=None)

    with patch("app.api.v1.campaigns.Campaign", MockCampaign):
        with pytest.raises(HTTPException) as exc_info:
            await delete_campaign(campaign_id="nonexistent", user=mock_user)

    assert exc_info.value.status_code == 404
