"""Unit tests for host API endpoints.

Tests call the async router functions directly.  All Beanie model
classes are mocked so that field access (``Host.ip``, ``Port.host_id``,
etc.) works without a live MongoDB backend.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.hosts import list_hosts, get_host, get_host_ports


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_auth_user(email="tester@netinsight.io"):
    """Mock authenticated user for ``user=Depends(require_auth)``."""
    user = MagicMock()
    user.email = email
    return user


def _mock_host_doc(host_id="host-001", ip="10.0.0.1", campaign_id="camp-001"):
    """Mock a Host Beanie document instance."""
    h = MagicMock()
    h.id = host_id
    h.ip = ip
    h.hostname = "web.example.com"
    h.mac_address = "aa:bb:cc:dd:ee:ff"
    h.os = "Linux 5.15"
    h.os_accuracy = 90
    h.status = "up"
    h.campaign_id = campaign_id
    h.first_seen = datetime(2026, 1, 1, tzinfo=timezone.utc)
    h.last_seen = datetime(2026, 6, 1, tzinfo=timezone.utc)
    return h


def _mock_port_doc(port_id="port-001", host_id="host-001", port=22):
    """Mock a Port Beanie document instance."""
    p = MagicMock()
    p.id = port_id
    p.host_id = host_id
    p.port = port
    p.protocol = "tcp"
    p.state = "open"
    p.service = "ssh"
    p.version = "OpenSSH 8.9"
    p.extra_info = None
    p.discovered_at = datetime(2026, 1, 15, tzinfo=timezone.utc)
    return p


def _make_chain(to_list=None, count=0):
    """Build a mock chain for ``.find().sort().to_list()`` / ``.count()``."""
    chain = MagicMock()
    chain.sort.return_value = chain
    chain.to_list = AsyncMock(return_value=to_list or [])
    chain.count = AsyncMock(return_value=count)
    return chain


# ---------------------------------------------------------------------------
# GET /hosts/
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_hosts():
    """GET /hosts/ — 200, returns list of HostDetail."""
    mock_host = _mock_host_doc()
    mock_user = _mock_auth_user()

    MockHost = MagicMock(name="Host")
    MockHost.find.return_value = _make_chain(to_list=[mock_host])
    MockHost.ip = MagicMock()  # for sort expression

    MockPort = MagicMock(name="Port")
    MockPort.find.return_value = _make_chain(count=2)
    MockPort.host_id = MagicMock()  # for query expression

    MockVuln = MagicMock(name="Vulnerability")
    MockVuln.find.return_value = _make_chain(count=1)
    MockVuln.host_id = MagicMock()

    with patch("app.api.v1.hosts.Host", MockHost), \
         patch("app.api.v1.hosts.Port", MockPort), \
         patch("app.api.v1.hosts.Vulnerability", MockVuln):
        result = await list_hosts(user=mock_user)

    assert len(result) == 1
    h = result[0]
    assert h.id == "host-001"
    assert h.ip == "10.0.0.1"
    assert h.hostname == "web.example.com"
    assert h.status == "up"
    assert h.port_count == 2
    assert h.vuln_count == 1


@pytest.mark.asyncio
async def test_list_hosts_empty():
    """GET /hosts/ — returns empty list when no hosts."""
    mock_user = _mock_auth_user()

    MockHost = MagicMock(name="Host")
    MockHost.find.return_value = _make_chain(to_list=[])
    MockHost.ip = MagicMock()

    with patch("app.api.v1.hosts.Host", MockHost):
        result = await list_hosts(user=mock_user)

    assert result == []


# ---------------------------------------------------------------------------
# GET /hosts/{host_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_host_found():
    """GET /hosts/{id} — 200 when host exists."""
    mock_host = _mock_host_doc()
    mock_user = _mock_auth_user()

    MockHost = MagicMock(name="Host")
    MockHost.get = AsyncMock(return_value=mock_host)

    MockPort = MagicMock(name="Port")
    MockPort.find.return_value = _make_chain(count=3)
    MockPort.host_id = MagicMock()

    MockVuln = MagicMock(name="Vulnerability")
    MockVuln.find.return_value = _make_chain(count=0)
    MockVuln.host_id = MagicMock()

    with patch("app.api.v1.hosts.Host", MockHost), \
         patch("app.api.v1.hosts.Port", MockPort), \
         patch("app.api.v1.hosts.Vulnerability", MockVuln):
        result = await get_host(host_id="host-001", user=mock_user)

    assert result.id == "host-001"
    assert result.ip == "10.0.0.1"
    assert result.port_count == 3
    assert result.vuln_count == 0


@pytest.mark.asyncio
async def test_get_host_not_found():
    """GET /hosts/{id} — 404 when host does not exist."""
    mock_user = _mock_auth_user()

    MockHost = MagicMock(name="Host")
    MockHost.get = AsyncMock(return_value=None)

    with patch("app.api.v1.hosts.Host", MockHost):
        with pytest.raises(HTTPException) as exc_info:
            await get_host(host_id="nonexistent", user=mock_user)

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# GET /hosts/{host_id}/ports
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_host_ports():
    """GET /hosts/{id}/ports — 200, returns list of PortResponse."""
    mock_host = _mock_host_doc()
    mock_port = _mock_port_doc()
    mock_user = _mock_auth_user()

    MockHost = MagicMock(name="Host")
    MockHost.get = AsyncMock(return_value=mock_host)

    MockPort = MagicMock(name="Port")
    MockPort.find.return_value = _make_chain(to_list=[mock_port])
    MockPort.host_id = MagicMock()
    MockPort.port = MagicMock()  # for sort expression

    with patch("app.api.v1.hosts.Host", MockHost), \
         patch("app.api.v1.hosts.Port", MockPort):
        result = await get_host_ports(host_id="host-001", user=mock_user)

    assert len(result) == 1
    p = result[0]
    assert p.id == "port-001"
    assert p.port == 22
    assert p.protocol == "tcp"
    assert p.service == "ssh"


@pytest.mark.asyncio
async def test_get_host_ports_host_not_found():
    """GET /hosts/{id}/ports — 404 when host does not exist."""
    mock_user = _mock_auth_user()

    MockHost = MagicMock(name="Host")
    MockHost.get = AsyncMock(return_value=None)

    with patch("app.api.v1.hosts.Host", MockHost):
        with pytest.raises(HTTPException) as exc_info:
            await get_host_ports(host_id="nonexistent", user=mock_user)

    assert exc_info.value.status_code == 404
