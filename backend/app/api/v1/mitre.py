"""MITRE ATT&CK knowledge base endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_auth
from app.models.mitre import MitreTechnique
from app.models.user import User

router = APIRouter(prefix="/mitre", tags=["MITRE ATT&CK"])

# Static tactics with descriptions
TACTICS = [
    {"id": "TA0043", "name": "Reconnaissance", "description": "Gathering information to plan future operations"},
    {"id": "TA0042", "name": "Resource Development", "description": "Establishing resources to support operations"},
    {"id": "TA0001", "name": "Initial Access", "description": "Getting into your network"},
    {"id": "TA0002", "name": "Execution", "description": "Running malicious code"},
    {"id": "TA0003", "name": "Persistence", "description": "Maintaining their foothold"},
    {"id": "TA0004", "name": "Privilege Escalation", "description": "Gaining higher-level permissions"},
    {"id": "TA0005", "name": "Defense Evasion", "description": "Avoiding being detected"},
    {"id": "TA0006", "name": "Credential Access", "description": "Stealing account names and passwords"},
    {"id": "TA0007", "name": "Discovery", "description": "Exploring your environment"},
    {"id": "TA0008", "name": "Lateral Movement", "description": "Moving through your environment"},
    {"id": "TA0009", "name": "Collection", "description": "Gathering data of interest"},
    {"id": "TA0011", "name": "Command and Control", "description": "Communicating with compromised systems"},
    {"id": "TA0010", "name": "Exfiltration", "description": "Stealing data"},
    {"id": "TA0040", "name": "Impact", "description": "Manipulate, interrupt, or destroy systems"},
]

# Core techniques from the service mapping (enriched)
CORE_TECHNIQUES = [
    {"id": "T1190", "name": "Exploit Public-Facing Application", "tactic": "Initial Access", "tactic_id": "TA0001", "url": "https://attack.mitre.org/techniques/T1190"},
    {"id": "T1592", "name": "Gather Victim Host Information", "tactic": "Reconnaissance", "tactic_id": "TA0043", "url": "https://attack.mitre.org/techniques/T1592"},
    {"id": "T1021.004", "name": "SSH", "tactic": "Lateral Movement", "tactic_id": "TA0008", "url": "https://attack.mitre.org/techniques/T1021/004"},
    {"id": "T1021.002", "name": "SMB/Windows Admin Shares", "tactic": "Lateral Movement", "tactic_id": "TA0008", "url": "https://attack.mitre.org/techniques/T1021/002"},
    {"id": "T1021.001", "name": "Remote Desktop Protocol", "tactic": "Lateral Movement", "tactic_id": "TA0008", "url": "https://attack.mitre.org/techniques/T1021/001"},
    {"id": "T1021", "name": "Remote Services", "tactic": "Lateral Movement", "tactic_id": "TA0008", "url": "https://attack.mitre.org/techniques/T1021"},
    {"id": "T1071.004", "name": "DNS", "tactic": "Command and Control", "tactic_id": "TA0011", "url": "https://attack.mitre.org/techniques/T1071/004"},
    {"id": "T1566", "name": "Phishing", "tactic": "Initial Access", "tactic_id": "TA0001", "url": "https://attack.mitre.org/techniques/T1566"},
    {"id": "T1087.002", "name": "Domain Account", "tactic": "Discovery", "tactic_id": "TA0007", "url": "https://attack.mitre.org/techniques/T1087/002"},
    {"id": "T1558", "name": "Steal or Forge Kerberos Tickets", "tactic": "Credential Access", "tactic_id": "TA0006", "url": "https://attack.mitre.org/techniques/T1558"},
    {"id": "T1059", "name": "Command and Scripting Interpreter", "tactic": "Execution", "tactic_id": "TA0002", "url": "https://attack.mitre.org/techniques/T1059"},
    {"id": "T1003", "name": "OS Credential Dumping", "tactic": "Credential Access", "tactic_id": "TA0006", "url": "https://attack.mitre.org/techniques/T1003"},
    {"id": "T1213", "name": "Data from Information Repositories", "tactic": "Collection", "tactic_id": "TA0009", "url": "https://attack.mitre.org/techniques/T1213"},
    {"id": "T1505", "name": "Server Software Component", "tactic": "Persistence", "tactic_id": "TA0003", "url": "https://attack.mitre.org/techniques/T1505"},
    {"id": "T1040", "name": "Network Sniffing", "tactic": "Discovery", "tactic_id": "TA0007", "url": "https://attack.mitre.org/techniques/T1040"},
]


@router.get("/tactics")
async def list_tactics(user: User = Depends(require_auth)):
    """List all MITRE ATT&CK tactics."""
    return TACTICS


@router.get("/techniques")
async def list_techniques(
    tactic: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: User = Depends(require_auth),
):
    """List MITRE ATT&CK techniques, optionally filtered by tactic or search."""
    from app.services.mitre_service import load_mitre_enterprise

    dataset = await load_mitre_enterprise()
    all_techniques = list(dataset.get("by_id", {}).values())

    # Map to expected frontend keys
    results = []
    for t in all_techniques:
        results.append({
            "id": t.get("technique_id", ""),
            "name": t.get("technique_name", ""),
            "tactic": t.get("tactic", ""),
            "tactic_id": t.get("tactic_id", ""),
            "description": t.get("description", ""),
            "url": t.get("url", ""),
        })

    if tactic:
        results = [t for t in results if t["tactic_id"] == tactic or t["tactic"].lower() == tactic.lower()]
    if search:
        q = search.lower()
        results = [t for t in results if q in t["id"].lower() or q in t["name"].lower()]
    return results[:200]


@router.get("/techniques/{technique_id}")
async def get_technique(technique_id: str, user: User = Depends(require_auth)):
    """Get a specific technique by ID from the full MITRE dataset."""
    from app.services.mitre_service import load_mitre_enterprise

    dataset = await load_mitre_enterprise()
    t = dataset.get("by_id", {}).get(technique_id.upper())
    if t:
        return {
            "id": t.get("technique_id", ""),
            "name": t.get("technique_name", ""),
            "tactic": t.get("tactic", ""),
            "tactic_id": t.get("tactic_id", ""),
            "description": t.get("description", ""),
            "url": t.get("url", ""),
        }
    raise HTTPException(status_code=404, detail="Technique not found")


@router.get("/full")
async def full_dataset(user: User = Depends(require_auth)):
    """Load and return the complete MITRE ATT&CK Enterprise dataset."""
    from app.services.mitre_service import load_mitre_enterprise

    dataset = await load_mitre_enterprise()
    return {
        "techniques": list(dataset.get("by_id", {}).values())[:500],
        "technique_count": len(dataset.get("by_id", {})),
    }


@router.get("/mappings")


async def list_mappings(
    technique_id: Optional[str] = Query(None),
    user: User = Depends(require_auth),
):
    """List stored MITRE technique mappings from scans."""
    query = {}
    if technique_id:
        query["technique_id"] = technique_id.upper()
    mappings = await MitreTechnique.find(query).limit(100).to_list()

    results = []
    for m in mappings:
        results.append({
            "id": str(m.id),
            "technique_id": m.technique_id,
            "technique_name": m.technique_name,
            "tactic": m.tactic,
            "tactic_id": m.tactic_id,
            "service_id": m.service_id,
            "vulnerability_id": m.vulnerability_id,
            "description": m.description,
            "url": m.url,
            "mapped_at": m.mapped_at.isoformat() if m.mapped_at else None,
        })
    return results


@router.get("/stats")
async def mitre_stats(user: User = Depends(require_auth)):
    """Get aggregate MITRE statistics."""
    mappings = await MitreTechnique.find_all().to_list()
    if not mappings:
        return {"total_mappings": 0, "unique_techniques": 0, "unique_tactics": 0, "by_tactic": []}

    technique_ids = set(m.technique_id for m in mappings)
    tactics = set(m.tactic for m in mappings)
    by_tactic: dict[str, int] = {}
    for m in mappings:
        by_tactic[m.tactic] = by_tactic.get(m.tactic, 0) + 1

    sorted_tactics = sorted(by_tactic.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_mappings": len(mappings),
        "unique_techniques": len(technique_ids),
        "unique_tactics": len(tactics),
        "by_tactic": [{"tactic": k, "count": v} for k, v in sorted_tactics],
    }
