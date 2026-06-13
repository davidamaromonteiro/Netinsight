"""
Celery tasks for sqlmap SQL injection scanning.

Provides:
    run_sqlmap_scan(scan_id)  – executes sqlmap against a target URL
"""

import asyncio
import logging
import re
from datetime import datetime, timezone

from app.tasks import celery_app, ensure_db_initialized, get_worker_loop

logger = logging.getLogger(__name__)


_CRITICAL_RE = re.compile(r"(?i)CRITICAL.*")


async def _run_sqlmap_async(scan_id: str) -> dict:
    """Run sqlmap against the specified target and persist results."""
    import subprocess
    import tempfile
    import os

    from app.core.validators import validate_sqlmap_args
    from app.models.sqlmap_scan import SqlmapScan, SqlmapScanStatus

    scan = await SqlmapScan.get(scan_id)
    if not scan:
        return {"status": "error", "message": f"Sqlmap scan {scan_id} not found"}

    scan.status = SqlmapScanStatus.RUNNING
    scan.started_at = datetime.now(timezone.utc)
    await scan.save()

    sqlmap_params: dict = scan.sqlmap_params or {}
    raw_args = sqlmap_params.get("sqlmap_args", "--batch")
    timeout_seconds = int(sqlmap_params.get("timeout_seconds", 1800))
    try:
        sanitized_args = validate_sqlmap_args(raw_args)
    except ValueError as exc:
        scan.status = SqlmapScanStatus.FAILED
        scan.result_summary = {"error": str(exc)}
        scan.completed_at = datetime.now(timezone.utc)
        await scan.save()
        return {"status": "error", "message": str(exc)}

    cmd = [
        "sqlmap",
        "-u", scan.target_url,
    ]
    cmd.extend(sanitized_args.split())

    # Add custom headers and cookies from sqlmap_params
    if sqlmap_params.get("headers"):
        cmd.extend(["--headers", sqlmap_params["headers"]])
    if sqlmap_params.get("cookie"):
        cmd.extend(["--cookie", sqlmap_params["cookie"]])
    if sqlmap_params.get("post_data"):
        cmd.extend(["--data", sqlmap_params["post_data"]])

    with tempfile.TemporaryDirectory() as tmpdir:
        env = os.environ.copy()
        env["HOME"] = tmpdir
        env["PYTHONUNBUFFERED"] = "1"

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=tmpdir,
            env=env,
        )

        output_lines: list[str] = []
        last_save = asyncio.get_event_loop().time()

        async def read_stream():
            nonlocal output_lines, last_save
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace")
                output_lines.append(decoded)

                now = asyncio.get_event_loop().time()
                if now - last_save > 3:
                    scan.raw_output = "".join(output_lines)[-50000:]
                    await scan.save()
                    last_save = now

        try:
            await asyncio.wait_for(read_stream(), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            scan.status = SqlmapScanStatus.FAILED
            scan.result_summary = {"error": f"Sqlmap scan timed out after {timeout_seconds // 60} minutes"}
            scan.completed_at = datetime.now(timezone.utc)
            if output_lines:
                scan.raw_output = "".join(output_lines)[-50000:]
            await scan.save()
            return {"status": "error", "message": "Scan timed out"}

        await process.wait()
        output = "".join(output_lines)

    # Parse results from output — extract structured vulnerability info
    vulnerabilities: list[dict] = []
    vulns_found = 0
    summary: dict = {}

    # Extract parameter-level vulnerability blocks from sqlmap output
    # Format:
    #   Parameter: q (GET)
    #       Type: boolean-based blind
    #       Title: ...
    #       Payload: ...
    param_match = re.findall(
        r"Parameter:\s+(\S+)\s+\((\S+)\).*?(?=---|\Z)",
        output, re.DOTALL,
    )
    type_matches = re.findall(r"Type:\s+(.+?)\n", output)
    title_matches = re.findall(r"Title:\s+(.+?)\n", output)
    payload_matches = re.findall(r"Payload:\s+(.+?)(?:\n|$)", output)

    for i in range(min(len(type_matches), len(title_matches))):
        vuln_type = type_matches[i].strip()
        title = title_matches[i].strip()
        payload = payload_matches[i].strip() if i < len(payload_matches) else ""
        param_name = param_match[i][0] if i < len(param_match) else "?"
        param_method = param_match[i][1] if i < len(param_match) else "GET"

        # Determine severity and technique
        severity = "HIGH"
        if "boolean-based blind" in vuln_type.lower():
            technique = "Boolean-based blind"
            severity = "MEDIUM"
            impact = "Permet d'extraire des données bit par bit en observant les différences de comportement (vrai/faux) de l'application."
        elif "error-based" in vuln_type.lower():
            technique = "Error-based"
            severity = "HIGH"
            impact = "Exploite les messages d'erreur SQL pour extraire des données. Rapide et fiable."
        elif "union query" in vuln_type.lower():
            technique = "UNION query"
            severity = "HIGH"
            impact = "Permet d'injecter une requête UNION pour lire directement les données d'autres tables dans la réponse HTTP."
        elif "time-based blind" in vuln_type.lower():
            technique = "Time-based blind"
            severity = "MEDIUM"
            impact = "Exploite les délais de réponse SQL (SLEEP) pour confirmer l'injection. Lent mais fiable."
        elif "stacked queries" in vuln_type.lower():
            technique = "Stacked queries"
            severity = "CRITICAL"
            impact = "Permet d'exécuter plusieurs requêtes SQL à la suite. Peut permettre INSERT/UPDATE/DELETE."
        elif "inline" in vuln_type.lower():
            technique = "Inline query"
            severity = "HIGH"
            impact = "Injection directe dans la requête originale. Résultats visibles dans la réponse."
        else:
            technique = vuln_type
            severity = "MEDIUM"
            impact = "Point d'injection SQL détecté. Peut permettre l'extraction de données ou la modification de la base."

        # MITRE ATT&CK mappings for SQL injection techniques
        mitre_map = {
            "Boolean-based blind": [
                {"id": "T1190", "name": "Exploit Public-Facing Application", "tactic": "Initial Access"},
                {"id": "T1059", "name": "Command and Scripting Interpreter", "tactic": "Execution"},
            ],
            "Error-based": [
                {"id": "T1190", "name": "Exploit Public-Facing Application", "tactic": "Initial Access"},
                {"id": "T1592", "name": "Gather Victim Host Information", "tactic": "Reconnaissance"},
            ],
            "UNION query": [
                {"id": "T1190", "name": "Exploit Public-Facing Application", "tactic": "Initial Access"},
                {"id": "T1003", "name": "OS Credential Dumping", "tactic": "Credential Access"},
                {"id": "T1213", "name": "Data from Information Repositories", "tactic": "Collection"},
            ],
            "Time-based blind": [
                {"id": "T1190", "name": "Exploit Public-Facing Application", "tactic": "Initial Access"},
            ],
            "Stacked queries": [
                {"id": "T1190", "name": "Exploit Public-Facing Application", "tactic": "Initial Access"},
                {"id": "T1505", "name": "Server Software Component", "tactic": "Persistence"},
            ],
        }
        mitre = mitre_map.get(technique, [
            {"id": "T1190", "name": "Exploit Public-Facing Application", "tactic": "Initial Access"},
        ])

        vulnerabilities.append({
            "parameter": param_name,
            "method": param_method,
            "type": vuln_type,
            "technique": technique,
            "title": title,
            "payload": payload[:300],
            "severity": severity,
            "impact": impact,
            "mitre_attack": mitre,
        })
        vulns_found += 1

    # Extract DBMS info
    dbms_match = re.search(r"(?i)back-end DBMS[:\s]+(?:is\s+)?'?(\w+)", output)
    if dbms_match:
        dbms_name = dbms_match.group(1).strip()
        summary["detected_dbms"] = dbms_name
        # CVE references for detected DBMS
        cve_map = {
            "MySQL": [{"id": "CVE-2024-21096", "cvss": 9.8, "desc": "Oracle MySQL privilege escalation via SQL injection"}],
            "PostgreSQL": [{"id": "CVE-2024-4317", "cvss": 8.1, "desc": "PostgreSQL pg_stats_ext SQL injection"}],
            "MSSQL": [{"id": "CVE-2024-2896", "cvss": 9.1, "desc": "Microsoft SQL Server remote code execution"}],
            "Oracle": [{"id": "CVE-2024-21182", "cvss": 9.8, "desc": "Oracle Database SQL injection in XML DB"}],
            "SQLite": [{"id": "CVE-2022-35737", "cvss": 7.5, "desc": "SQLite array-bounds overflow via crafted SQL"}],
        }
        for key, cves in cve_map.items():
            if key.lower() in dbms_name.lower():
                summary["related_cves"] = cves
                break

    # Critical warnings
    critical_matches = _CRITICAL_RE.findall(output)
    if critical_matches:
        summary["critical_warnings"] = len(critical_matches)

    summary["vulnerabilities"] = vulnerabilities

    # Extract dumped table data from output
    # Format:
    #   Database: <current>
    #   Table: users
    #   [4 entries]
    #   +----+--------+----------+
    #   | id | email  | password |
    #   +----+--------+----------+
    #   | 1  | a@b.c  | hash     |
    #   +----+--------+----------+
    dumped_tables: list[dict] = []
    table_blocks = re.split(r"\n(?=Database:)", output)
    for block in table_blocks:
        db_match = re.search(r"Database:\s+(.+)", block)
        table_match = re.search(r"Table:\s+(.+)", block)
        entries_match = re.search(r"\[(\d+)\s+entr", block)
        if not table_match:
            continue

        table_name = table_match.group(1).strip()
        db_name = db_match.group(1).strip() if db_match else "current"
        entry_count = int(entries_match.group(1)) if entries_match else 0

        columns: list[str] = []
        rows: list[list[str]] = []

        lines = block.split("\n")
        sep_count = 0
        for line in lines:
            line = line.strip()
            if line.startswith("+---"):
                sep_count += 1
                continue
            if line.startswith("|") and (sep_count == 1 or sep_count == 2):
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if sep_count == 1:
                    columns = cells
                else:
                    rows.append(cells)

        if columns and rows:
            dumped_tables.append({
                "database": db_name,
                "table": table_name,
                "entries": entry_count,
                "columns": columns,
                "rows": rows[:200],
            })

    if dumped_tables:
        summary["dumped_tables"] = dumped_tables
        vulns_found = max(vulns_found, 1)

    # Update scan document
    scan.status = SqlmapScanStatus.COMPLETED
    scan.completed_at = datetime.now(timezone.utc)
    scan.vulnerabilities_found = vulns_found
    scan.result_summary = summary
    scan.raw_output = output[:50000] if len(output) > 50000 else output

    await scan.save()

    logger.info(
        "Sqlmap scan %s completed: %d vulnerabilities found",
        scan.name,
        vulns_found,
    )

    return {
        "status": "ok",
        "message": f"Sqlmap scan completed: {vulns_found} injection(s) found",
        "vulnerabilities_found": vulns_found,
    }


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60, soft_time_limit=3600)
def run_sqlmap_scan(self, scan_id: str) -> dict:
    """Execute a sqlmap scan against the target URL."""
    ensure_db_initialized()
    loop = get_worker_loop()
    try:
        return loop.run_until_complete(_run_sqlmap_async(scan_id))
    except Exception as exc:
        logger.exception("run_sqlmap_scan failed for scan_id=%s", scan_id)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "error", "message": f"Max retries exceeded: {exc}"}
