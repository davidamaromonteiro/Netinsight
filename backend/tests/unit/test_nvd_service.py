"""Unit tests for nvd_service — NVD CVE lookup and enrichment."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.nvd_service import (
    NvdRateLimiter,
    _infer_severity,
    _parse_nvd_response,
    lookup_cves,
)

# ---------------------------------------------------------------------------
# Sample NVD API 2.0 response payloads
# ---------------------------------------------------------------------------

SAMPLE_NVD_RESPONSE = {
    "vulnerabilities": [
        {
            "cve": {
                "id": "CVE-2024-6387",
                "descriptions": [
                    {"lang": "en", "value": "A signal handler race condition was found in OpenSSH."}
                ],
                "metrics": {
                    "cvssMetricV31": [
                        {
                            "cvssData": {
                                "baseScore": 8.1,
                                "baseSeverity": "HIGH",
                                "vectorString": "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:H",
                            }
                        }
                    ]
                },
                "references": [
                    {"url": "https://nvd.nist.gov/vuln/detail/CVE-2024-6387"},
                    {"url": "https://www.qualys.com/regresshion-cve-2024-6387/"},
                ],
                "published": "2024-07-01T04:15:00.000",
                "lastModified": "2024-07-15T12:15:00.000",
            }
        }
    ]
}


SAMPLE_NVD_EMPTY = {"vulnerabilities": []}


SAMPLE_NVD_V2_FALLBACK = {
    "vulnerabilities": [
        {
            "cve": {
                "id": "CVE-2019-6111",
                "descriptions": [
                    {"lang": "en", "value": "An issue in OpenSSH scp."}
                ],
                "metrics": {
                    "cvssMetricV2": [
                        {
                            "cvssData": {
                                "baseScore": 5.8,
                                "baseSeverity": "MEDIUM",
                                "vectorString": "AV:N/AC:M/Au:N/C:N/I:P/A:P",
                            }
                        }
                    ]
                },
                "references": [],
                "published": "2019-01-25T00:00:00.000",
                "lastModified": "2019-02-15T00:00:00.000",
            }
        }
    ]
}

# ---------------------------------------------------------------------------
# _infer_severity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "score,expected",
    [
        (10.0, "CRITICAL"),
        (9.0, "CRITICAL"),
        (8.9, "HIGH"),
        (7.0, "HIGH"),
        (6.9, "MEDIUM"),
        (4.0, "MEDIUM"),
        (3.9, "LOW"),
        (0.1, "LOW"),
        (0.0, "NONE"),
        (-1.0, "NONE"),
    ],
)
def test_infer_severity(score, expected):
    """Map CVSS numeric scores to human-readable severity labels."""
    assert _infer_severity(score) == expected


# ---------------------------------------------------------------------------
# _parse_nvd_response
# ---------------------------------------------------------------------------


def test_parse_nvd_response_v31():
    """Correctly extract CVSS v3.1 data from an NVD response."""
    results = _parse_nvd_response(SAMPLE_NVD_RESPONSE)

    assert len(results) == 1
    cve = results[0]
    assert cve["cve_id"] == "CVE-2024-6387"
    assert cve["cvss_score"] == 8.1
    assert cve["severity"] == "HIGH"
    assert cve["vector"] == "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:H"
    assert "signal handler" in cve["description"].lower()
    assert len(cve["references"]) == 2
    assert cve["published_date"] == "2024-07-01T04:15:00.000"


def test_parse_nvd_response_v2_fallback():
    """Fall back to CVSS v2.0 when v3.x metrics are absent."""
    results = _parse_nvd_response(SAMPLE_NVD_V2_FALLBACK)

    assert len(results) == 1
    cve = results[0]
    assert cve["cve_id"] == "CVE-2019-6111"
    assert cve["cvss_score"] == 5.8
    assert cve["severity"] == "MEDIUM"


def test_parse_nvd_response_empty():
    """Return an empty list when the response contains no vulnerabilities."""
    results = _parse_nvd_response(SAMPLE_NVD_EMPTY)
    assert results == []


def test_parse_nvd_response_missing_fields():
    """Gracefully handle missing optional fields."""
    data = {
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-2999-9999",
                    "descriptions": [],
                    "metrics": {},
                    "references": [],
                }
            }
        ]
    }
    results = _parse_nvd_response(data)

    assert len(results) == 1
    cve = results[0]
    assert cve["cve_id"] == "CVE-2999-9999"
    assert cve["cvss_score"] is None
    assert cve["severity"] is None
    assert cve["description"] is None
    assert cve["references"] == []


# ---------------------------------------------------------------------------
# lookup_cves
# ---------------------------------------------------------------------------


def _make_mock_response(json_body: dict, status_code: int = 200):
    """Build a mock httpx.Response-like object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error",
            request=MagicMock(),
            response=MagicMock(status_code=status_code),
        )
    resp.json.return_value = json_body
    return resp


def _build_mock_async_client(get_return_value=None, get_side_effect=None):
    """Build a mock ``httpx.AsyncClient`` whose ``__aenter__`` returns the
    *same* mock so that ``client.get`` resolves to the configured AsyncMock."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client  # *critical*: reuse self
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.get = AsyncMock(
        return_value=get_return_value,
        side_effect=get_side_effect,
    )
    return mock_client


@pytest.mark.asyncio
async def test_lookup_cves_mock_response():
    """Parse a real-looking NVD response and return structured CVE data."""
    mock_client = _build_mock_async_client(
        get_return_value=_make_mock_response(SAMPLE_NVD_RESPONSE)
    )

    with patch("httpx.AsyncClient", return_value=mock_client):
        results = await lookup_cves("openssh", "9.2p1")

    assert len(results) == 1
    assert results[0]["cve_id"] == "CVE-2024-6387"
    assert results[0]["cvss_score"] == 8.1


@pytest.mark.asyncio
async def test_lookup_cves_empty_response():
    """Return an empty list when the NVD has no matching CVEs."""
    mock_client = _build_mock_async_client(
        get_return_value=_make_mock_response(SAMPLE_NVD_EMPTY)
    )

    with patch("httpx.AsyncClient", return_value=mock_client):
        results = await lookup_cves("fake-service-no-cves", "99.99")

    assert results == []


@pytest.mark.asyncio
async def test_lookup_cves_http_error():
    """Return an empty list (graceful degradation) on HTTP errors."""
    mock_client = _build_mock_async_client(
        get_return_value=_make_mock_response({}, status_code=503)
    )

    with patch("httpx.AsyncClient", return_value=mock_client):
        results = await lookup_cves("openssh", "9.2p1")

    assert results == []


@pytest.mark.asyncio
async def test_lookup_cves_network_error():
    """Return an empty list on network / timeout errors."""
    mock_client = _build_mock_async_client(
        get_side_effect=httpx.TimeoutException("timed out")
    )

    with patch("httpx.AsyncClient", return_value=mock_client):
        results = await lookup_cves("nginx", "1.25")

    assert results == []


# ---------------------------------------------------------------------------
# NvdRateLimiter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limiter_waits():
    """Enforce the minimum interval between successive requests."""
    limiter = NvdRateLimiter(has_api_key=False)

    start = time.monotonic()
    await limiter.wait()
    await limiter.wait()
    elapsed = time.monotonic() - start

    # Without an API key the minimum interval is 6 seconds between
    # requests.  The two waits should total at least 6 s.
    assert elapsed >= 6.0, f"Expected >=6.0 s, got {elapsed:.2f} s"


@pytest.mark.asyncio
async def test_rate_limiter_with_api_key():
    """Use a shorter interval when an API key is configured."""
    limiter = NvdRateLimiter(has_api_key=True)

    start = time.monotonic()
    await limiter.wait()
    await limiter.wait()
    elapsed = time.monotonic() - start

    # With an API key the interval drops to 0.6 s → total ≥ 0.6 s
    assert 0.5 < elapsed < 5.0, f"Expected ~0.6-5.0 s, got {elapsed:.2f} s"


@pytest.mark.asyncio
async def test_rate_limiter_first_call_immediate():
    """The very first call to wait() should return immediately."""
    limiter = NvdRateLimiter(has_api_key=False)

    start = time.monotonic()
    await limiter.wait()
    elapsed = time.monotonic() - start

    assert elapsed < 0.2, f"First call should be instant, got {elapsed:.2f} s"
