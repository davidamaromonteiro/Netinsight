"""
NVD enrichment service.

Queries the National Vulnerability Database (NVD API 2.0) to enrich
detected services with CVE data.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class NvdRateLimiter:
    """Token-bucket–style rate limiter for the NVD API.

    Without an API key the NVD enforces 6 requests per rolling 30-second
    window.  With a key that increases to ~50 requests / 30 s.  We implement
    the conservative (no-key) behaviour by default and relax the interval
    when a key is present.
    """

    def __init__(self, has_api_key: bool = False) -> None:
        self._last_request = 0.0
        self._min_interval = 0.6 if has_api_key else 6.0

    async def wait(self) -> None:
        """Block until the minimum interval since the last request has elapsed."""
        now = time.monotonic()
        elapsed = now - self._last_request
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request = time.monotonic()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _infer_severity(score: float) -> str:
    """Map a CVSS numeric score to a human-readable severity label."""
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MEDIUM"
    if score >= 0.1:
        return "LOW"
    return "NONE"


def _parse_nvd_response(data: dict) -> list[dict]:
    """Extract vulnerability data from a raw NVD API 2.0 JSON response.

    Args:
        data: Decoded JSON body returned by the NVD ``/cves/2.0`` endpoint.

    Returns:
        A list of dicts, each containing keys suitable for constructing a
        ``Vulnerability`` document: ``cve_id``, ``cvss_score``,
        ``severity``, ``description``, ``vector``, ``published_date``,
        ``references``.

        CVSS v3.1 metrics are preferred; v2.0 is used as a fallback.
        The English description is selected when available.
    """
    results: list[dict] = []

    for vuln_item in data.get("vulnerabilities", []):
        cve = vuln_item.get("cve", {})
        cve_id = cve.get("id", "")

        # --- CVSS metrics (v3.1 > v2.0) -----------------------------------
        cvss_score: Optional[float] = None
        severity: Optional[str] = None
        vector: Optional[str] = None

        metrics = cve.get("metrics", {})

        for metric_key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            metric_list = metrics.get(metric_key, [])
            if not metric_list:
                continue
            cvss_data = metric_list[0].get("cvssData", {})
            cvss_score = cvss_data.get("baseScore")
            severity = cvss_data.get("baseSeverity")
            vector = cvss_data.get("vectorString")
            if cvss_score is not None:
                break

        if severity is None and cvss_score is not None:
            severity = _infer_severity(cvss_score)

        # --- Description (prefer English) ----------------------------------
        description: Optional[str] = None
        for desc in cve.get("descriptions", []):
            if desc.get("lang") == "en":
                description = desc.get("value")
                break
        if description is None and cve.get("descriptions"):
            # Fallback to the first description regardless of language
            description = cve["descriptions"][0].get("value")

        # --- References ----------------------------------------------------
        references: list[str] = [
            ref.get("url", "")
            for ref in cve.get("references", [])
            if ref.get("url")
        ]

        # --- Dates ---------------------------------------------------------
        published_date: Optional[str] = cve.get("published")
        last_modified: Optional[str] = cve.get("lastModified")

        results.append(
            {
                "cve_id": cve_id,
                "cvss_score": cvss_score,
                "severity": severity,
                "description": description,
                "vector": vector,
                "published_date": published_date,
                "last_modified": last_modified,
                "references": references,
            }
        )

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def lookup_cves(
    service_name: str,
    version: Optional[str] = None,
) -> list[dict]:
    """Search the NVD API 2.0 for CVEs matching a service name and version.

    Args:
        service_name: The name of the service (e.g. ``"openssh"``, ``"nginx"``).
        version: Optional version string to narrow results
            (e.g. ``"9.2p1"``).

    Returns:
        A list of dicts formatted for ``Vulnerability`` document creation
        (see :func:`_parse_nvd_response` for the dict schema).

    Note:
        Rate-limiting is enforced internally via :class:`NvdRateLimiter`.
        A warning is logged on HTTP or network errors and an empty list is
        returned so that a single failure does not abort the whole
        enrichment process.
    """
    settings = get_settings()
    api_key = settings.NVD_API_KEY
    base_url = settings.NVD_API_BASE_URL.rstrip("/")

    # Build the keyword search string
    keyword_parts = [service_name]
    if version:
        keyword_parts.append(version)
    keyword_search = " ".join(keyword_parts)

    params: dict = {
        "keywordSearch": keyword_search,
        "resultsPerPage": 50,
    }
    headers: dict = {
        "User-Agent": "NetInsight/0.2.0",
        "Accept": "application/json",
    }
    if api_key:
        headers["apiKey"] = api_key

    rate_limiter = NvdRateLimiter(has_api_key=bool(api_key))

    try:
        await rate_limiter.wait()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{base_url}",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "NVD API returned HTTP %d for service '%s' (version=%s): %s",
            exc.response.status_code,
            service_name,
            version,
            exc,
        )
        return []
    except (httpx.RequestError, httpx.TimeoutException) as exc:
        logger.warning(
            "NVD API request failed for service '%s' (version=%s): %s",
            service_name,
            version,
            exc,
        )
        return []

    cves = _parse_nvd_response(data)
    logger.info(
        "NVD lookup for '%s' (version=%s): %d CVE(s) found",
        service_name,
        version,
        len(cves),
    )
    return cves


async def enrich_host_vulnerabilities(host_id: str) -> dict:
    """Scan all services on a host and persist any newly discovered CVEs.

    For every port that has a ``service`` field set, the NVD API is queried.
    New Vulnerability documents are created, skipping duplicates (same
    ``cve_id`` + ``host_id`` + ``service_id``).

    Args:
        host_id: The Beanie document ID of the :class:`Host`.

    Returns:
        A summary dict::

            {
                "host_id": "...",
                "vulns_found": 12,   # total CVEs returned by NVD
                "vulns_new": 5,      # CVEs that did not exist yet in DB
            }
    """
    # Lazy imports to avoid circular dependencies
    from app.models.host import Host  # noqa: E402
    from app.models.port import Port  # noqa: E402
    from app.models.service import Service  # noqa: E402
    from app.models.vulnerability import Vulnerability  # noqa: E402

    host = await Host.get(host_id)
    if not host:
        logger.warning("Host %s not found – skipping vulnerability enrichment", host_id)
        return {"host_id": host_id, "vulns_found": 0, "vulns_new": 0}

    ports = await Port.find(Port.host_id == host_id).to_list()

    vulns_found = 0
    vulns_new = 0

    for port in ports:
        # Port-based fallback when service detection fails
        service_name = port.service
        if (not service_name or service_name in ("tcpwrapped", "unknown", "generic")) and port.port:
            _PORT_MAP = {21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns", 80: "http", 110: "pop3",
                         143: "imap", 389: "ldap", 443: "https", 445: "smb", 993: "imaps", 3306: "mysql",
                         3389: "rdp", 5432: "postgresql", 6379: "redis", 8080: "http", 8443: "https", 27017: "mongodb"}
            service_name = _PORT_MAP.get(port.port, service_name)

        if not service_name or service_name == "tcpwrapped":
            continue

        service_doc: Service | None = None
        # Try to match a Service record linked to this port
        services = await Service.find(
            Service.host_id == host_id,
            Service.port_id == str(port.id),
        ).to_list()
        service_doc = services[0] if services else None

        cves = await lookup_cves(service_name, port.version)

        for cve_data in cves:
            vulns_found += 1

            # Deduplication
            existing = await Vulnerability.find_one(
                Vulnerability.cve_id == cve_data["cve_id"],
                Vulnerability.host_id == host_id,
                Vulnerability.service_id == (
                    str(service_doc.id) if service_doc else ""
                ),
            )
            if existing is not None:
                continue

            # Parse date strings if present
            published_date = None
            if cve_data.get("published_date"):
                from dateutil.parser import parse as parse_date

                try:
                    published_date = parse_date(cve_data["published_date"])
                except (ValueError, TypeError):
                    published_date = None

            last_modified = None
            if cve_data.get("last_modified"):
                from dateutil.parser import parse as parse_date

                try:
                    last_modified = parse_date(cve_data["last_modified"])
                except (ValueError, TypeError):
                    last_modified = None

            vuln = Vulnerability(
                host_id=host_id,
                service_id=str(service_doc.id) if service_doc else "",
                campaign_id=host.campaign_id,
                cve_id=cve_data["cve_id"],
                cvss_score=cve_data.get("cvss_score"),
                severity=cve_data.get("severity"),
                description=cve_data.get("description"),
                vector=cve_data.get("vector"),
                published_date=published_date,
                last_modified=last_modified,
                references=cve_data.get("references") or [],
            )
            await vuln.insert()
            vulns_new += 1

    logger.info(
        "Host %s vuln enrichment done: %d found, %d new",
        host_id,
        vulns_found,
        vulns_new,
    )
    return {"host_id": host_id, "vulns_found": vulns_found, "vulns_new": vulns_new}


async def enrich_campaign_vulnerabilities(campaign_id: str) -> dict:
    """Enrich all hosts belonging to a campaign with NVD vulnerability data.

    Args:
        campaign_id: The Beanie document ID of the campaign.

    Returns:
        An aggregated summary dict::

            {
                "campaign_id": "...",
                "total_vulns_found": 42,
                "total_vulns_new": 15,
                "hosts_processed": 3,
            }
    """
    # Lazy imports to avoid circular dependencies
    from app.models.host import Host  # noqa: E402

    hosts = await Host.find(Host.campaign_id == campaign_id).to_list()

    total_found = 0
    total_new = 0

    for host in hosts:
        result = await enrich_host_vulnerabilities(str(host.id))
        total_found += result["vulns_found"]
        total_new += result["vulns_new"]

    logger.info(
        "Campaign %s vuln enrichment done: %d found, %d new across %d host(s)",
        campaign_id,
        total_found,
        total_new,
        len(hosts),
    )
    return {
        "campaign_id": campaign_id,
        "total_vulns_found": total_found,
        "total_vulns_new": total_new,
        "hosts_processed": len(hosts),
    }
