"""
MITRE ATT&CK mapping service.

Downloads the MITRE ATT&CK Enterprise dataset and maps detected services,
ports, and vulnerabilities to MITRE techniques.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static service → technique mapping (curated, always available)
# ---------------------------------------------------------------------------

SERVICE_MITRE_MAP: dict[str, list[tuple[str, str, str, str]]] = {
    "ssh": [
        ("T1021.004", "SSH", "Lateral Movement", "TA0008"),
    ],
    "http": [
        ("T1190", "Exploit Public-Facing Application", "Initial Access", "TA0001"),
        ("T1592", "Gather Victim Host Information", "Reconnaissance", "TA0043"),
    ],
    "https": [
        ("T1190", "Exploit Public-Facing Application", "Initial Access", "TA0001"),
    ],
    "smb": [
        ("T1021.002", "SMB/Windows Admin Shares", "Lateral Movement", "TA0008"),
        ("T1043", "Commonly Used Port", "Command and Control", "TA0011"),
    ],
    "rdp": [
        ("T1021.001", "Remote Desktop Protocol", "Lateral Movement", "TA0008"),
    ],
    "mysql": [
        ("T1190", "Exploit Public-Facing Application", "Initial Access", "TA0001"),
    ],
    "postgresql": [
        ("T1190", "Exploit Public-Facing Application", "Initial Access", "TA0001"),
    ],
    "ftp": [
        ("T1190", "Exploit Public-Facing Application", "Initial Access", "TA0001"),
    ],
    "telnet": [
        ("T1021", "Remote Services", "Lateral Movement", "TA0008"),
    ],
    "dns": [
        ("T1071.004", "DNS", "Command and Control", "TA0011"),
    ],
    "smtp": [
        ("T1566", "Phishing", "Initial Access", "TA0001"),
    ],
    "ldap": [
        ("T1087.002", "Domain Account", "Discovery", "TA0007"),
    ],
    "kerberos": [
        ("T1558", "Steal or Forge Kerberos Tickets", "Credential Access", "TA0006"),
    ],
}

# ---- Port-based fallback when service detection fails (tcpwrapped/unknown) ----
PORT_TO_SERVICE: dict[int, str] = {
    21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp",
    53: "dns", 80: "http", 110: "pop3", 113: "ident",
    135: "epmap", 139: "netbios", 143: "imap", 389: "ldap",
    443: "https", 445: "smb", 465: "smtps", 554: "rtsp",
    587: "smtp", 636: "ldaps", 993: "imaps", 995: "pop3s",
    1433: "mssql", 1521: "oracle", 2049: "nfs", 3306: "mysql",
    3389: "rdp", 5432: "postgresql", 5900: "vnc", 6379: "redis",
    8080: "http", 8443: "https", 27017: "mongodb",
}

# ---------------------------------------------------------------------------
# Module-level cache for the remote MITRE dataset
# ---------------------------------------------------------------------------

_mitre_cache: dict[str, Any] | None = None
"""In-memory cache holding the parsed & indexed MITRE ATT&CK dataset.

Structure:
    {
        "raw": {  # full parsed JSON from the upstream URL
            "type": "bundle",
            "objects": [...],
        },
        "by_name": {
            "exploit public-facing application": {
                "technique_id": "T1190",
                "technique_name": "Exploit Public-Facing Application",
                "tactic": "Initial Access",
                "tactic_id": "TA0001",
                "description": "...",
                "url": "https://attack.mitre.org/techniques/T1190",
            },
            ...
        },
        "by_id": {
            "T1190": { ... },
            ...
        },
    }
"""

# ---------------------------------------------------------------------------
# Helpers – MITRE STIX parsing
# ---------------------------------------------------------------------------


def _tactic_short_to_long() -> dict[str, tuple[str, str]]:
    """Return a mapping from STIX phase_name (lowercase, hyphenated) to
    (tactic_name, tactic_id).  Built at import time from a canonical list
    rather than relying on the remote dataset so that the static
    SERVICE_MITRE_MAP validates immediately."""
    return {
        "reconnaissance": ("Reconnaissance", "TA0043"),
        "resource-development": ("Resource Development", "TA0042"),
        "initial-access": ("Initial Access", "TA0001"),
        "execution": ("Execution", "TA0002"),
        "persistence": ("Persistence", "TA0003"),
        "privilege-escalation": ("Privilege Escalation", "TA0004"),
        "defense-evasion": ("Defense Evasion", "TA0005"),
        "credential-access": ("Credential Access", "TA0006"),
        "discovery": ("Discovery", "TA0007"),
        "lateral-movement": ("Lateral Movement", "TA0008"),
        "collection": ("Collection", "TA0009"),
        "command-and-control": ("Command and Control", "TA0011"),
        "exfiltration": ("Exfiltration", "TA0010"),
        "impact": ("Impact", "TA0040"),
    }


_TACTIC_LOOKUP: dict[str, tuple[str, str]] = _tactic_short_to_long()


def _parse_mitre_stix(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse the MITRE ATT&CK STIX bundle into an indexed structure.

    Args:
        raw: The full JSON payload loaded from the upstream URL.

    Returns:
        A dict with ``by_name`` and ``by_id`` indexes.  Each entry is a
        lightweight technique summary dict suitable for populating
        ``MitreTechnique`` documents.
    """
    by_name: dict[str, dict[str, Any]] = {}
    by_id: dict[str, dict[str, Any]] = {}

    # -- Helper: find the MITRE external reference --------------------------
    def _ext_ref(external_references: list[dict]) -> tuple[str, str]:
        """Return (external_id, url) from the mitre-attack reference."""
        for ref in external_references:
            if ref.get("source_name") == "mitre-attack":
                return ref.get("external_id", ""), ref.get("url", "")
        return "", ""

    # -- Pass 1: index tactics by their STIX id for fast lookup ------------
    tactic_by_stix_id: dict[str, tuple[str, str]] = {}
    for obj in raw.get("objects", []):
        if obj.get("type") == "x-mitre-tactic":
            stix_id = obj.get("id", "")
            ext_id, _ = _ext_ref(obj.get("external_references", []))
            tac_name = obj.get("name", "")
            phase_short = obj.get("x_mitre_shortname", "")
            if stix_id:
                tactic_by_stix_id[stix_id] = (tac_name, ext_id)
            if phase_short and phase_short not in _TACTIC_LOOKUP:
                _TACTIC_LOOKUP[phase_short] = (tac_name, ext_id)

    # -- Pass 2: parse attack-patterns (techniques & sub-techniques) --------
    for obj in raw.get("objects", []):
        if obj.get("type") != "attack-pattern":
            continue

        ext_id, url = _ext_ref(obj.get("external_references", []))
        if not ext_id:
            continue

        name: str = obj.get("name", "")
        description: str = obj.get("description", "")

        # Determine tactic(s) from kill_chain_phases
        tactic_name = ""
        tactic_id = ""
        for phase in obj.get("kill_chain_phases", []):
            if phase.get("kill_chain_name") == "mitre-attack":
                phase_name: str = phase.get("phase_name", "")
                if phase_name in _TACTIC_LOOKUP:
                    tactic_name, tactic_id = _TACTIC_LOOKUP[phase_name]
                    break

        entry = {
            "technique_id": ext_id,
            "technique_name": name,
            "tactic": tactic_name,
            "tactic_id": tactic_id,
            "description": description,
            "url": url,
        }

        by_id[ext_id.upper()] = entry
        by_name[name.lower()] = entry

    return {"by_name": by_name, "by_id": by_id}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def load_mitre_enterprise() -> dict[str, Any]:
    """Download (once) and index the MITRE ATT&CK Enterprise dataset.

    The result is cached in memory so subsequent calls return instantly.

    Returns:
        A dict with keys ``by_name`` and ``by_id``, each mapping to
        technique summary dicts.
    """
    global _mitre_cache

    if _mitre_cache is not None:
        return _mitre_cache

    settings = get_settings()
    url = settings.MITRE_ENTERPRISE_URL

    logger.info("Downloading MITRE ATT&CK Enterprise dataset from %s", url)

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        response = await client.get(url)
        response.raise_for_status()
        raw = response.json()

    indexed = _parse_mitre_stix(raw)
    _mitre_cache = indexed
    logger.info(
        "MITRE ATT&CK dataset loaded: %d techniques indexed",
        len(indexed.get("by_id", {})),
    )
    return _mitre_cache


async def map_service_to_mitre(
    service_name: str,
    port: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Map a service name (and optional port number) to MITRE techniques.

    The mapping uses a two-step strategy:

    1. **Static lookup** – the built-in ``SERVICE_MITRE_MAP`` dictionary
       (always available, no network round-trip).
    2. **Fuzzy match** – if the service name is not in the static map,
       the loaded MITRE ATT&CK dataset is searched for techniques whose
       name or description contains the given service name.

    Args:
        service_name: Normalised service name (e.g. ``"ssh"``, ``"http"``).
        port: Optional numeric port for additional context (currently unused
            but reserved for future heuristics).

    Returns:
        A list of technique dicts, each containing the keys required by
        ``MitreTechnique``: ``technique_id``, ``technique_name``, ``tactic``,
        ``tactic_id``, ``description``, and ``url``.
    """
    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    # 0 -- Port-based fallback when service detection fails
    unknown_service = (not service_name or service_name in ("tcpwrapped", "unknown", "generic"))
    if unknown_service and port is not None and port in PORT_TO_SERVICE:
        inferred = PORT_TO_SERVICE[port]
        logger.debug("Port %d → inferred service %s (was %s)", port, inferred, service_name)
        service_name = inferred

    # 1 -- Static mapping (always checked first)
    static_entries = SERVICE_MITRE_MAP.get(service_name.lower(), [])
    for tech_id, tech_name, tactic, tactic_id in static_entries:
        if tech_id in seen_ids:
            continue
        seen_ids.add(tech_id)
        results.append(
            {
                "technique_id": tech_id,
                "technique_name": tech_name,
                "tactic": tactic,
                "tactic_id": tactic_id,
                "description": None,
                "url": f"https://attack.mitre.org/techniques/{tech_id}",
            }
        )

    # 2 -- Fuzzy match against the loaded dataset (only for services NOT in static map)
    if service_name.lower() not in SERVICE_MITRE_MAP:
        try:
            dataset = await load_mitre_enterprise()
        except Exception:
            logger.warning("Could not load MITRE dataset for fuzzy match", exc_info=True)
            return results

        query = service_name.lower()
        matched = 0
        for name, entry in dataset.get("by_name", {}).items():
            if entry["technique_id"] in seen_ids:
                continue
            # Word-boundary match (not substring)
            desc = (entry.get("description") or "").lower()
            if query in name.split() or f" {query} " in f" {desc} ":
                seen_ids.add(entry["technique_id"])
                results.append(
                    {
                        "technique_id": entry["technique_id"],
                        "technique_name": entry["technique_name"],
                        "tactic": entry["tactic"],
                        "tactic_id": entry["tactic_id"],
                        "description": entry.get("description"),
                        "url": entry.get("url"),
                    }
                )
                matched += 1
                if matched >= 5:  # limit per service
                    break

        if matched:
            logger.debug("MITRE fuzzy: %d techniques for %r", matched, service_name)
    return results


async def map_host_ports_to_mitre(host_id: str) -> dict[str, Any]:
    """Map all open ports of a host to MITRE ATT&CK techniques.

    For each port that has a recognised service, the appropriate
    ``MitreTechnique`` document is created (if it does not already exist).
    Duplicates are prevented by checking the combination
    ``(technique_id, service_id)``, where ``service_id`` is the port's
    document ID.

    Args:
        host_id: The Beanie document ID of the host.

    Returns:
        A summary dict::

            {
                "host_id": str,
                "techniques_found": int,   # total mappings found
                "techniques_new": int,     # newly persisted documents
            }
    """
    # Lazy imports to avoid circular deps with Beanie
    from app.models.mitre import MitreTechnique
    from app.models.port import Port

    ports = await Port.find(Port.host_id == host_id).to_list()

    techniques_found = 0
    techniques_new = 0

    for port_doc in ports:
        service = (port_doc.service or "").lower().strip()
        if not service:
            continue

        mappings = await map_service_to_mitre(service, port=port_doc.port)

        for mapping in mappings:
            techniques_found += 1

            # Check for existing document to avoid duplicates
            existing = await MitreTechnique.find_one(
                MitreTechnique.technique_id == mapping["technique_id"],
                MitreTechnique.service_id == str(port_doc.id),
            )
            if existing is not None:
                continue

            mitre_doc = MitreTechnique(
                service_id=str(port_doc.id),
                technique_id=mapping["technique_id"],
                technique_name=mapping["technique_name"],
                tactic=mapping["tactic"],
                tactic_id=mapping["tactic_id"],
                description=mapping.get("description"),
                url=mapping.get("url"),
            )
            await mitre_doc.insert()
            techniques_new += 1

    logger.info(
        "Host %s: %d MITRE mappings found, %d new documents created",
        host_id,
        techniques_found,
        techniques_new,
    )

    return {
        "host_id": host_id,
        "techniques_found": techniques_found,
        "techniques_new": techniques_new,
    }


async def map_campaign_to_mitre(campaign_id: str) -> dict[str, Any]:
    """Map every host in a campaign to MITRE ATT&CK techniques.

    Iterates over all hosts belonging to the campaign and delegates to
    :func:`map_host_ports_to_mitre` for each host, then returns an
    aggregated summary.

    Args:
        campaign_id: The Beanie document ID of the campaign.

    Returns:
        A summary dict::

            {
                "campaign_id": str,
                "hosts_scanned": int,
                "hosts_with_findings": int,
                "techniques_found": int,
                "techniques_new": int,
                "details": [
                    { "host_id": ..., "techniques_found": ..., "techniques_new": ... },
                    ...
                ],
            }
    """
    # Lazy imports to avoid circular deps
    from app.models.host import Host

    hosts = await Host.find(Host.campaign_id == campaign_id).to_list()

    hosts_scanned = 0
    hosts_with_findings = 0
    total_found = 0
    total_new = 0
    details: list[dict[str, Any]] = []

    for host in hosts:
        summary = await map_host_ports_to_mitre(str(host.id))
        hosts_scanned += 1
        total_found += summary["techniques_found"]
        total_new += summary["techniques_new"]
        if summary["techniques_new"] > 0:
            hosts_with_findings += 1
        details.append(summary)

    logger.info(
        "Campaign %s: %d hosts scanned, %d with findings, "
        "%d techniques found, %d new records",
        campaign_id,
        hosts_scanned,
        hosts_with_findings,
        total_found,
        total_new,
    )

    return {
        "campaign_id": campaign_id,
        "hosts_scanned": hosts_scanned,
        "hosts_with_findings": hosts_with_findings,
        "techniques_found": total_found,
        "techniques_new": total_new,
        "details": details,
    }
