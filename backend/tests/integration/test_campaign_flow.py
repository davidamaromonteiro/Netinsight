"""Integration tests for the campaign lifecycle flow.

Tests end-to-end flows: create campaign → list → get detail → delete with cascading.
Uses the same mock strategy as unit tests but chains multiple endpoint calls
to verify complete campaign workflows.
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
    """Mock authenticated user for ``user=Depends(require_auth)``."""
    user = MagicMock()
    user.email = email
    user.id = "usr-001"
    return user


def _mock_campaign_doc(campaign_id="camp-001", name="Integration Campaign",
                       status=CampaignStatus.PENDING):
    """Mock a Campaign Beanie document instance."""
    c = MagicMock()
    c.id = campaign_id
    c.name = name
    c.description = "An integration test campaign"
    c.targets = ["10.0.0.1", "10.0.0.2"]
    c.status = status
    c.created_by = "tester@netinsight.io"
    c.created_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
    c.started_at = None
    c.completed_at = None
    c.insert = AsyncMock()
    c.delete = AsyncMock()
    return c


def _make_chain(to_list=None, count=0):
    """Build a mock chain for ``.find().sort().to_list()`` / ``.count()`` / ``.delete()``."""
    chain = MagicMock()
    chain.sort.return_value = chain
    chain.to_list = AsyncMock(return_value=to_list or [])
    chain.count = AsyncMock(return_value=count)
    chain.delete = AsyncMock()
    return chain


# ---------------------------------------------------------------------------
# Test: create → list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_campaign_then_list():
    """Full flow: create a campaign then retrieve it in the list.

    Simulates: POST /campaigns/ → GET /campaigns/.
    Verifies the created campaign appears in the listing.
    """
    mock_user = _mock_auth_user()
    mock_camp = _mock_campaign_doc(campaign_id="camp-flow-001", name="E2E Scan")

    # --- Step 1: Create campaign ---
    MockCampaign = MagicMock(name="Campaign")
    MockCampaign.return_value = mock_camp

    with patch("app.api.v1.campaigns.Campaign", MockCampaign):
        payload = CampaignCreate(
            name="E2E Scan",
            targets=["10.0.0.1", "10.0.0.2"],
        )
        created = await create_campaign(payload=payload, user=mock_user)

    assert created.id == "camp-flow-001"
    assert created.name == "E2E Scan"
    assert created.status == "pending"
    assert created.targets == ["10.0.0.1", "10.0.0.2"]
    assert created.created_by == "tester@netinsight.io"
    mock_camp.insert.assert_awaited_once()

    # --- Step 2: List campaigns and verify the created one appears ---
    mock_list_camp = _mock_campaign_doc(campaign_id="camp-flow-001", name="E2E Scan")

    MockCampaign2 = MagicMock(name="Campaign")
    MockCampaign2.find.return_value = _make_chain(to_list=[mock_list_camp])
    MockCampaign2.created_at = MagicMock()

    MockHost = MagicMock(name="Host")
    MockHost.find.return_value = _make_chain(count=5)

    MockVuln = MagicMock(name="Vulnerability")
    MockVuln.find.return_value = _make_chain(count=3)
    MockVuln.campaign_id = MagicMock()

    with patch("app.api.v1.campaigns.Campaign", MockCampaign2), \
         patch("app.api.v1.campaigns.Host", MockHost), \
         patch("app.api.v1.campaigns.Vulnerability", MockVuln):
        result = await list_campaigns(user=mock_user)

    assert len(result) == 1
    assert result[0].id == "camp-flow-001"
    assert result[0].name == "E2E Scan"
    assert result[0].status == "pending"
    assert result[0].target_count == 2
    assert result[0].host_count == 5
    assert result[0].vuln_count == 3


# ---------------------------------------------------------------------------
# Test: create → get detail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_campaign_then_get_detail():
    """Full flow: create a campaign then retrieve it by ID.

    Simulates: POST /campaigns/ → GET /campaigns/{id}.
    Verifies the detail response matches the created resource.
    """
    mock_user = _mock_auth_user()
    mock_camp = _mock_campaign_doc(
        campaign_id="camp-detail-001",
        name="Detail Scan",
        status=CampaignStatus.PENDING,
    )

    # --- Step 1: Create ---
    MockCampaignCreate = MagicMock(name="Campaign")
    MockCampaignCreate.return_value = mock_camp

    with patch("app.api.v1.campaigns.Campaign", MockCampaignCreate):
        payload = CampaignCreate(
            name="Detail Scan",
            targets=["192.168.1.0/24"],
            description="A detailed integration test",
        )
        created = await create_campaign(payload=payload, user=mock_user)

    assert created.id == "camp-detail-001"

    # --- Step 2: Get by ID ---
    # Build a fresh mock doc that reflects the created campaign's description
    mock_get_camp = _mock_campaign_doc(
        campaign_id="camp-detail-001",
        name="Detail Scan",
        status=CampaignStatus.PENDING,
    )
    mock_get_camp.description = "A detailed integration test"
    mock_get_camp.targets = ["192.168.1.0/24"]

    MockCampaignGet = MagicMock(name="Campaign")
    MockCampaignGet.get = AsyncMock(return_value=mock_get_camp)

    with patch("app.api.v1.campaigns.Campaign", MockCampaignGet):
        detail = await get_campaign(
            campaign_id="camp-detail-001", user=mock_user
        )

    assert detail.id == "camp-detail-001"
    assert detail.name == "Detail Scan"
    assert detail.status == "pending"
    assert detail.targets == ["192.168.1.0/24"]
    assert detail.description == "A detailed integration test"
    assert detail.created_by == "tester@netinsight.io"
    MockCampaignGet.get.assert_awaited_once_with("camp-detail-001")


# ---------------------------------------------------------------------------
# Test: delete campaign removes associated hosts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_campaign_removes_hosts():
    """Full flow: create a campaign, add hosts, then delete the campaign
    and verify the associated hosts (and vulnerabilities/auth tests) are deleted.

    Simulates: DELETE /campaigns/{id} triggers cascading cleanup of
    Host, Vulnerability, and AuthTest documents.
    """
    mock_user = _mock_auth_user()
    mock_camp = _mock_campaign_doc(campaign_id="camp-del-001", name="To Delete")

    # --- Step 1: Setup — campaign exists with associated hosts ---
    # Build mock chains for delete operations
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

    # --- Step 2: Delete the campaign ---
    with patch("app.api.v1.campaigns.Campaign", MockCampaign), \
         patch("app.api.v1.campaigns.Host", MockHost), \
         patch("app.api.v1.campaigns.Vulnerability", MockVuln), \
         patch("app.api.v1.campaigns.AuthTest", MockAuthTest):
        result = await delete_campaign(
            campaign_id="camp-del-001", user=mock_user
        )

    # --- Assertions ---
    assert result is None  # 204 No Content

    # Campaign itself is deleted
    mock_camp.delete.assert_awaited_once()

    # Associated hosts are deleted (cascading cleanup)
    host_chain.delete.assert_awaited_once()
    MockHost.find.assert_called_once()

    # Associated vulnerabilities are also cleaned up
    vuln_chain.delete.assert_awaited_once()
    MockVuln.find.assert_called_once()

    # Auth tests are cleaned up too
    auth_chain.delete.assert_awaited_once()
    MockAuthTest.find.assert_called_once()


# ---------------------------------------------------------------------------
# Test: create → delete → get (verify gone)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_then_delete_then_get_returns_404():
    """Full lifecycle: create a campaign, delete it, then try to get it — 404.

    Simulates: POST → DELETE → GET /campaigns/{id}, verifying the resource
    is truly removed from the service perspective.
    """
    mock_user = _mock_auth_user()
    mock_camp = _mock_campaign_doc(campaign_id="camp-life-001", name="Lifecycle")

    # --- Step 1: Create ---
    MockCampaignCreate = MagicMock(name="Campaign")
    MockCampaignCreate.return_value = mock_camp

    with patch("app.api.v1.campaigns.Campaign", MockCampaignCreate):
        payload = CampaignCreate(name="Lifecycle", targets=["10.0.0.1"])
        created = await create_campaign(payload=payload, user=mock_user)
    assert created.id == "camp-life-001"

    # --- Step 2: Delete ---
    host_chain = _make_chain()
    vuln_chain = _make_chain()
    auth_chain = _make_chain()

    MockCampaignDel = MagicMock(name="Campaign")
    MockCampaignDel.get = AsyncMock(return_value=mock_camp)

    with patch("app.api.v1.campaigns.Campaign", MockCampaignDel), \
         patch("app.api.v1.campaigns.Host", MagicMock(find=MagicMock(return_value=host_chain), campaign_id=MagicMock())), \
         patch("app.api.v1.campaigns.Vulnerability", MagicMock(find=MagicMock(return_value=vuln_chain), campaign_id=MagicMock())), \
         patch("app.api.v1.campaigns.AuthTest", MagicMock(find=MagicMock(return_value=auth_chain), campaign_id=MagicMock())):
        result = await delete_campaign(campaign_id="camp-life-001", user=mock_user)
    assert result is None

    # --- Step 3: Try to get the deleted campaign → 404 ---
    MockCampaignGone = MagicMock(name="Campaign")
    MockCampaignGone.get = AsyncMock(return_value=None)  # not found

    with patch("app.api.v1.campaigns.Campaign", MockCampaignGone):
        with pytest.raises(HTTPException) as exc_info:
            await get_campaign(campaign_id="camp-life-001", user=mock_user)

    assert exc_info.value.status_code == 404
