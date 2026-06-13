"""Unit tests for mitre_service — MITRE ATT&CK mapping."""

from __future__ import annotations

import copy
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.mitre_service import (
    SERVICE_MITRE_MAP,
    _parse_mitre_stix,
    load_mitre_enterprise,
    map_service_to_mitre,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_DATASET_EMPTY = {"by_name": {}, "by_id": {}}


def _mock_mitre(http_response_json: dict | None = None):
    """Context manager that mocks ``httpx.AsyncClient`` (and therefore
    ``load_mitre_enterprise``) returning the provided STIX bundle.

    The mock's ``__aenter__`` returns the *same* object so that
    ``client.get`` resolves to the configured AsyncMock."""
    bundle = http_response_json or {"objects": []}
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(
        return_value=_make_json_response(bundle)
    )
    return patch("httpx.AsyncClient", return_value=mock_client)


def _make_json_response(json_body: dict):
    """Build a mock httpx.Response-like object."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = json_body
    return resp


# ---------------------------------------------------------------------------
# _parse_mitre_stix
# ---------------------------------------------------------------------------


def test_parse_mitre_stix_empty_bundle():
    """An empty STIX bundle yields empty indexes."""
    result = _parse_mitre_stix({"objects": []})
    assert result == {"by_name": {}, "by_id": {}}


def test_parse_mitre_stix_with_technique():
    """A bundle with one attack-pattern is correctly indexed."""
    bundle = {
        "objects": [
            {
                "type": "attack-pattern",
                "id": "attack-pattern--01",
                "name": "Exploit Public-Facing Application",
                "description": "Adversaries may attempt to exploit...",
                "kill_chain_phases": [
                    {
                        "kill_chain_name": "mitre-attack",
                        "phase_name": "initial-access",
                    }
                ],
                "external_references": [
                    {
                        "source_name": "mitre-attack",
                        "external_id": "T1190",
                        "url": "https://attack.mitre.org/techniques/T1190",
                    }
                ],
            }
        ]
    }
    result = _parse_mitre_stix(bundle)

    assert "T1190" in result["by_id"]
    assert "exploit public-facing application" in result["by_name"]

    entry = result["by_id"]["T1190"]
    assert entry["technique_name"] == "Exploit Public-Facing Application"
    assert entry["tactic"] == "Initial Access"
    assert entry["tactic_id"] == "TA0001"


# ---------------------------------------------------------------------------
# load_mitre_enterprise
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_mitre_enterprise_mock():
    """Download and parse the MITRE ATT&CK dataset via mocked HTTP."""
    import app.services.mitre_service as ms

    # Reset the module-level cache so this test always fetches
    ms._mitre_cache = None

    bundle = {
        "objects": [
            {
                "type": "attack-pattern",
                "id": "attack-pattern--02",
                "name": "Phishing",
                "description": "Adversaries may send phishing messages...",
                "kill_chain_phases": [
                    {
                        "kill_chain_name": "mitre-attack",
                        "phase_name": "initial-access",
                    }
                ],
                "external_references": [
                    {
                        "source_name": "mitre-attack",
                        "external_id": "T1566",
                        "url": "https://attack.mitre.org/techniques/T1566",
                    }
                ],
            }
        ]
    }

    with _mock_mitre(bundle):
        result = await load_mitre_enterprise()

    assert "by_name" in result
    assert "by_id" in result
    assert "T1566" in result["by_id"]
    assert result["by_id"]["T1566"]["technique_name"] == "Phishing"


@pytest.mark.asyncio
async def test_load_mitre_enterprise_cached():
    """Second call returns the cached dataset without HTTP."""
    import app.services.mitre_service as ms

    ms._mitre_cache = MOCK_DATASET_EMPTY

    # Should not trigger any HTTP call — returns cached immediately
    with patch("httpx.AsyncClient") as mock_client_class:
        result = await load_mitre_enterprise()

    mock_client_class.assert_not_called()
    assert result == MOCK_DATASET_EMPTY


# ---------------------------------------------------------------------------
# map_service_to_mitre — static lookups
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_map_service_to_mitre_ssh():
    """SSH maps to T1021.004 (SSH / Lateral Movement)."""
    with patch(
        "app.services.mitre_service.load_mitre_enterprise",
        AsyncMock(return_value=MOCK_DATASET_EMPTY),
    ):
        results = await map_service_to_mitre("ssh")

    technique_ids = {r["technique_id"] for r in results}
    assert "T1021.004" in technique_ids
    # At least the static entry (possibly more from fuzzy match)
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_map_service_to_mitre_http():
    """HTTP maps to T1190 (Initial Access) and T1592 (Reconnaissance)."""
    with patch(
        "app.services.mitre_service.load_mitre_enterprise",
        AsyncMock(return_value=MOCK_DATASET_EMPTY),
    ):
        results = await map_service_to_mitre("http")

    technique_ids = {r["technique_id"] for r in results}
    assert "T1190" in technique_ids
    assert "T1592" in technique_ids
    assert len(results) >= 2


@pytest.mark.asyncio
async def test_map_service_to_mitre_https():
    """HTTPS maps to T1190 (Initial Access)."""
    with patch(
        "app.services.mitre_service.load_mitre_enterprise",
        AsyncMock(return_value=MOCK_DATASET_EMPTY),
    ):
        results = await map_service_to_mitre("https")

    technique_ids = {r["technique_id"] for r in results}
    assert "T1190" in technique_ids


@pytest.mark.asyncio
async def test_map_service_to_mitre_smb():
    """SMB maps to T1021.002 (Lateral Movement) and T1043 (C2)."""
    with patch(
        "app.services.mitre_service.load_mitre_enterprise",
        AsyncMock(return_value=MOCK_DATASET_EMPTY),
    ):
        results = await map_service_to_mitre("smb")

    technique_ids = {r["technique_id"] for r in results}
    assert "T1021.002" in technique_ids
    assert "T1043" in technique_ids


@pytest.mark.asyncio
async def test_map_service_to_mitre_unknown():
    """An unrecognised service returns an empty list."""
    with patch(
        "app.services.mitre_service.load_mitre_enterprise",
        AsyncMock(return_value=MOCK_DATASET_EMPTY),
    ):
        results = await map_service_to_mitre("nonexistent-service-xyz")

    assert results == []


@pytest.mark.asyncio
async def test_map_service_to_mitre_case_insensitive():
    """Service names are matched case-insensitively."""
    with patch(
        "app.services.mitre_service.load_mitre_enterprise",
        AsyncMock(return_value=MOCK_DATASET_EMPTY),
    ):
        results_lower = await map_service_to_mitre("ssh")
        results_upper = await map_service_to_mitre("SSH")
        results_mixed = await map_service_to_mitre("Ssh")

    assert results_lower == results_upper == results_mixed


# ---------------------------------------------------------------------------
# map_service_to_mitre — fuzzy matching
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_map_service_to_mitre_fuzzy_match():
    """When no static entry exists, fall back to fuzzy match against the
    loaded MITRE dataset."""
    dataset = {
        "by_name": {
            "windows admin shares": {
                "technique_id": "T1021.002",
                "technique_name": "Windows Admin Shares",
                "tactic": "Lateral Movement",
                "tactic_id": "TA0008",
                "description": "Adversaries may use SMB/Windows Admin Shares...",
                "url": "https://attack.mitre.org/techniques/T1021/002",
            }
        },
        "by_id": {},
    }

    with patch(
        "app.services.mitre_service.load_mitre_enterprise",
        AsyncMock(return_value=dataset),
    ):
        # "admin shares" is a substring of "windows admin shares"
        results = await map_service_to_mitre("admin shares")

    assert len(results) >= 1
    assert any(r["technique_id"] == "T1021.002" for r in results)


# ---------------------------------------------------------------------------
# Static mapping consistency
# ---------------------------------------------------------------------------


def test_service_mitre_map_no_duplicate_ids():
    """No technique ID appears more than once per service entry."""
    for service, entries in SERVICE_MITRE_MAP.items():
        ids = [e[0] for e in entries]
        assert len(ids) == len(set(ids)), (
            f"Duplicate technique ID in SERVICE_MITRE_MAP['{service}']"
        )
