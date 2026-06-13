"""
Celery tasks for Nikto web server scanning.
"""
import asyncio
import logging
import re
from datetime import datetime, timezone

from app.tasks import celery_app, ensure_db_initialized, get_worker_loop

logger = logging.getLogger(__name__)


async def _run_nikto_async(scan_id: str) -> dict:
    """Run Nikto against the target and persist results."""
    import subprocess
    import tempfile
    import os

    from app.models.nikto_scan import NiktoScan, NiktoScanStatus

    scan = await NiktoScan.get(scan_id)
    if not scan:
        return {"status": "error", "message": f"Nikto scan {scan_id} not found"}

    scan.status = NiktoScanStatus.RUNNING
    scan.started_at = datetime.now(timezone.utc)
    await scan.save()

    protocol = "https" if scan.use_ssl else "http"
    host = scan.target_host
    port = scan.target_port

    cmd = [
        "nikto",
        "-h", f"{protocol}://{host}:{port}",
        "-Format", "txt",
        "-nointeractive",
        "-Tuning", "1234567890abcde",
    ]

    # Add custom params
    nikto_params = scan.nikto_params or {}
    if nikto_params.get("timeout"):
        cmd.extend(["-timeout", str(nikto_params["timeout"])])

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        raw_output = ""
        try:
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=600)
            raw_output = stdout.decode("utf-8", errors="replace")
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            scan.status = NiktoScanStatus.FAILED
            scan.result_summary = {"error": "Nikto scan timed out after 10 minutes"}
            scan.completed_at = datetime.now(timezone.utc)
            await scan.save()
            return {"status": "error", "message": "Scan timed out"}

    except FileNotFoundError:
        scan.status = NiktoScanStatus.FAILED
        scan.result_summary = {"error": "Nikto not installed"}
        scan.completed_at = datetime.now(timezone.utc)
        await scan.save()
        return {"status": "error", "message": "Nikto not installed"}

    # Parse results
    vulnerabilities: list[dict] = []
    vulns_found = 0
    summary: dict = {}

    # Extract OSVDB/CVE references
    osvdb_matches = re.findall(r"OSVDB-(\d+)", raw_output)
    cve_matches = re.findall(r"(CVE-\d{4}-\d+)", raw_output)

    # Count findings by severity
    high_count = len(re.findall(r"(?i)vulnerable|critical|remote\s+code\s+execution", raw_output))
    medium_count = len(re.findall(r"(?i)interesting|information\s+disclosure|directory\s+indexing", raw_output))
    low_count = len(re.findall(r"(?i)allowed\s+http|cookie|server\s+leaks|clickjacking", raw_output))

    # Extract server info
    server_match = re.search(r"Server:\s*(.+)", raw_output)
    if server_match:
        summary["server"] = server_match.group(1).strip()
    
    # Extract interesting headers
    header_matches = re.findall(r"^\+\s+(.+?):\s*(.+)", raw_output, re.MULTILINE)
    interesting_headers = []
    for key, value in header_matches:
        if any(h in key.lower() for h in ("x-frame", "x-content", "x-xss", "strict-transport", "content-security", "x-powered")):
            interesting_headers.append({"header": key, "value": value.strip()})

    if interesting_headers:
        summary["interesting_headers"] = interesting_headers

    # Count total findings
    all_findings = re.findall(r"^\+\s+(.+?)$", raw_output, re.MULTILINE)
    vulns_found = len(all_findings)

    # Categorize findings
    for finding in all_findings[:50]:  # limit to 50
        finding_clean = finding.strip()
        if not finding_clean:
            continue

        severity = "MEDIUM"
        if any(w in finding_clean.lower() for w in ("critical", "rce", "remote code execution", "sqli", "command injection")):
            severity = "CRITICAL"
        elif any(w in finding_clean.lower() for w in ("vulnerable", "xss", "csrf", "directory traversal")):
            severity = "HIGH"
        elif any(w in finding_clean.lower() for w in ("information", "disclosure", "cookie", "clickjacking")):
            severity = "LOW"

        # Extract CVE if present
        cve_match = re.search(r"CVE-\d{4}-\d+", finding_clean)
        
        vuln = {
            "finding": finding_clean[:300],
            "severity": severity,
            "cve_id": cve_match.group(0) if cve_match else None,
        }
        vulnerabilities.append(vuln)

    summary["vulnerabilities"] = vulnerabilities
    summary["total_findings"] = vulns_found
    summary["high_findings"] = high_count
    summary["medium_findings"] = medium_count
    summary["low_findings"] = low_count
    summary["osvdb_refs"] = len(osvdb_matches)
    summary["cve_refs"] = len(cve_matches)

    # MITRE mappings
    mitre_techniques = []
    if high_count > 0:
        mitre_techniques.append({"id": "T1190", "name": "Exploit Public-Facing Application", "tactic": "Initial Access"})
    if medium_count > 0:
        mitre_techniques.append({"id": "T1592", "name": "Gather Victim Host Information", "tactic": "Reconnaissance"})
    if low_count > 0:
        mitre_techniques.append({"id": "T1082", "name": "System Information Discovery", "tactic": "Discovery"})
    summary["mitre_techniques"] = mitre_techniques

    scan.status = NiktoScanStatus.COMPLETED
    scan.completed_at = datetime.now(timezone.utc)
    scan.vulnerabilities_found = vulns_found
    scan.result_summary = summary
    scan.raw_output = raw_output[-100000:]

    await scan.save()

    logger.info(
        "Nikto scan %s completed: %d findings (%dH/%dM/%dL)",
        scan.name, vulns_found, high_count, medium_count, low_count,
    )

    return {
        "status": "ok",
        "message": f"Nikto scan completed: {vulns_found} findings",
        "high": high_count,
        "medium": medium_count,
        "low": low_count,
    }


@celery_app.task(bind=True, max_retries=1, default_retry_delay=60, soft_time_limit=900)
def run_nikto_scan(self, scan_id: str) -> dict:
    """Execute a Nikto scan against the target."""
    ensure_db_initialized()
    loop = get_worker_loop()
    try:
        return loop.run_until_complete(_run_nikto_async(scan_id))
    except Exception as exc:
        logger.exception("run_nikto_scan failed for scan_id=%s", scan_id)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "error", "message": str(exc)}
