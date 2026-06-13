"""Unit tests for Beanie document models — validation and defaults."""

from datetime import datetime, timezone

import pytest

from app.models.campaign import Campaign, CampaignStatus
from app.models.host import Host
from app.models.port import Port
from app.models.vulnerability import Vulnerability


# ---------------------------------------------------------------------------
# Campaign model
# ---------------------------------------------------------------------------


def test_create_campaign_model():
    """Campaign model instantiation with valid fields."""
    campaign = Campaign(
        name="Security Audit Q1",
        description="Quarterly security scan",
        targets=["10.0.0.1", "192.168.1.0/24"],
        created_by="analyst@example.com",
    )

    assert campaign.name == "Security Audit Q1"
    assert campaign.description == "Quarterly security scan"
    assert campaign.targets == ["10.0.0.1", "192.168.1.0/24"]
    assert campaign.status == CampaignStatus.PENDING
    assert campaign.created_by == "analyst@example.com"
    assert isinstance(campaign.created_at, datetime)
    assert campaign.started_at is None
    assert campaign.completed_at is None
    assert campaign.scan_params == {}


def test_campaign_defaults():
    """Campaign model uses correct default values."""
    campaign = Campaign(
        name="Minimal Campaign",
        targets=["10.0.0.1"],
    )

    assert campaign.status == CampaignStatus.PENDING
    assert campaign.description is None
    assert campaign.created_by is None
    assert campaign.scan_params == {}
    assert campaign.started_at is None
    assert campaign.completed_at is None


def test_campaign_status_enum():
    """CampaignStatus enum has all expected values."""
    assert CampaignStatus.PENDING.value == "pending"
    assert CampaignStatus.RUNNING.value == "running"
    assert CampaignStatus.COMPLETED.value == "completed"
    assert CampaignStatus.FAILED.value == "failed"
    assert CampaignStatus.CANCELLED.value == "cancelled"

    # Enum members are strings
    assert isinstance(CampaignStatus.PENDING, str)


# ---------------------------------------------------------------------------
# Host model
# ---------------------------------------------------------------------------


def test_create_host_model():
    """Host model instantiation with required + default fields."""
    host = Host(
        ip="10.0.0.5",
        campaign_id="camp-001",
    )

    assert host.ip == "10.0.0.5"
    assert host.campaign_id == "camp-001"
    assert host.status == "unknown"
    assert host.hostname is None
    assert host.mac_address is None
    assert host.os is None
    assert host.os_accuracy is None
    assert isinstance(host.first_seen, datetime)
    assert isinstance(host.last_seen, datetime)


def test_host_first_seen_last_seen():
    """Host model sets first_seen and last_seen to current UTC time by default."""
    host = Host(ip="10.0.0.6", campaign_id="camp-001")

    assert host.first_seen.tzinfo is not None
    assert host.last_seen.tzinfo is not None


# ---------------------------------------------------------------------------
# Port model
# ---------------------------------------------------------------------------


def test_create_port_model():
    """Port model instantiation with defaults."""
    port = Port(
        host_id="host-001",
        port=443,
    )

    assert port.host_id == "host-001"
    assert port.port == 443
    assert port.protocol == "tcp"
    assert port.state == "open"
    assert port.service is None
    assert port.version is None
    assert port.extra_info is None
    assert isinstance(port.discovered_at, datetime)


def test_port_with_udp_protocol():
    """Port model can represent UDP ports."""
    port = Port(
        host_id="host-001",
        port=53,
        protocol="udp",
        service="dns",
    )

    assert port.protocol == "udp"
    assert port.service == "dns"


# ---------------------------------------------------------------------------
# Vulnerability model
# ---------------------------------------------------------------------------


def test_create_vulnerability_model():
    """Vulnerability model instantiation with optional fields None by default."""
    vuln = Vulnerability(
        host_id="host-001",
        service_id="svc-001",
        cve_id="CVE-2024-12345",
    )

    assert vuln.host_id == "host-001"
    assert vuln.service_id == "svc-001"
    assert vuln.cve_id == "CVE-2024-12345"
    assert vuln.cvss_score is None
    assert vuln.severity is None
    assert vuln.description is None
    assert vuln.vector is None
    assert vuln.published_date is None
    assert vuln.last_modified is None
    assert vuln.references == []
    assert isinstance(vuln.discovered_at, datetime)


def test_create_vulnerability_with_cvss():
    """Vulnerability model with CVSS score and severity."""
    vuln = Vulnerability(
        host_id="host-001",
        service_id="svc-001",
        cve_id="CVE-2024-99999",
        cvss_score=9.8,
        severity="CRITICAL",
        description="Remote code execution",
        vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    )

    assert vuln.cvss_score == 9.8
    assert vuln.severity == "CRITICAL"
    assert vuln.description == "Remote code execution"
    assert "AV:N" in vuln.vector
