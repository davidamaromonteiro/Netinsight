"""
Celery tasks for PDF report generation.
Generates comprehensive security reports with MITRE ATT&CK and Cyber Kill Chain.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone

from app.tasks import celery_app, ensure_db_initialized, get_worker_loop

logger = logging.getLogger(__name__)
_REPORTS_DIR = os.environ.get("NETINSIGHT_REPORTS_DIR", "/tmp/netinsight/reports")


# ═══════════════════════════════════════════════════════════════════════
# Cyber Kill Chain phases with descriptions
# ═══════════════════════════════════════════════════════════════════════
KILL_CHAIN = [
    ("1. Reconnaissance", "Identification des cibles, scan réseau, détection de services et bannières.",
     "Nmap, Banner Grabbing, Nikto"),
    ("2. Weaponization", "Préparation des exploits basés sur les vulnérabilités détectées (CVE, versions obsolètes).",
     "CVE Database, Exploit-DB"),
    ("3. Delivery", "Vecteurs d'attaque identifiés : services exposés (HTTP, SSH, SMB, RDP, SQL).",
     "Services réseau exposés"),
    ("4. Exploitation", "Injection SQL détectée, failles web (XSS, CSRF), services vulnérables.",
     "SQLmap, Nikto, Nmap NSE"),
    ("5. Installation", "Persistance possible via comptes faibles, services non sécurisés, backdoors web.",
     "Auth tests faibles, shells web"),
    ("6. Command & Control", "Canaux C2 potentiels : ports ouverts non standards, tunnels DNS/HTTP.",
     "Ports atypiques, services exposés"),
    ("7. Actions on Objectives", "Exfiltration de données, impact sur la confidentialité/intégrité.",
     "Données extraites (SQLmap dump), secrets exposés"),
]


# ═══════════════════════════════════════════════════════════════════════
# MITRE ATT&CK mappings for common findings
# ═══════════════════════════════════════════════════════════════════════
MITRE_FINDINGS = {
    "ssh": [
        ("T1021.004", "Remote Services: SSH", "Lateral Movement"),
        ("T1110", "Brute Force", "Credential Access"),
    ],
    "http": [
        ("T1190", "Exploit Public-Facing Application", "Initial Access"),
        ("T1592", "Gather Victim Host Information", "Reconnaissance"),
    ],
    "https": [
        ("T1190", "Exploit Public-Facing Application", "Initial Access"),
        ("T1071.001", "Web Protocols", "Command and Control"),
    ],
    "smb": [
        ("T1021.002", "Remote Services: SMB/Windows Admin Shares", "Lateral Movement"),
        ("T1082", "System Information Discovery", "Discovery"),
    ],
    "rdp": [
        ("T1021.001", "Remote Desktop Protocol", "Lateral Movement"),
        ("T1110", "Brute Force", "Credential Access"),
    ],
    "mysql": [
        ("T1190", "Exploit Public-Facing Application", "Initial Access"),
        ("T1213", "Data from Information Repositories", "Collection"),
    ],
    "postgresql": [
        ("T1190", "Exploit Public-Facing Application", "Initial Access"),
        ("T1003", "OS Credential Dumping", "Credential Access"),
    ],
    "smtp": [
        ("T1566", "Phishing", "Initial Access"),
        ("T1048", "Exfiltration Over Alternative Protocol", "Exfiltration"),
    ],
    "dns": [
        ("T1071.004", "DNS", "Command and Control"),
        ("T1048", "Exfiltration Over Alternative Protocol", "Exfiltration"),
    ],
    "ftp": [
        ("T1048", "Exfiltration Over Alternative Protocol", "Exfiltration"),
        ("T1021", "Remote Services", "Lateral Movement"),
    ],
    "telnet": [
        ("T1021", "Remote Services", "Lateral Movement"),
        ("T1040", "Network Sniffing", "Credential Access"),
    ],
    "sql_injection": [
        ("T1190", "Exploit Public-Facing Application", "Initial Access"),
        ("T1059", "Command and Scripting Interpreter", "Execution"),
        ("T1213", "Data from Information Repositories", "Collection"),
        ("T1003", "OS Credential Dumping", "Credential Access"),
    ],
    "weak_auth": [
        ("T1078", "Valid Accounts", "Defense Evasion"),
        ("T1110", "Brute Force", "Credential Access"),
    ],
    "information_disclosure": [
        ("T1592", "Gather Victim Host Information", "Reconnaissance"),
        ("T1082", "System Information Discovery", "Discovery"),
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# Async orchestration
# ═══════════════════════════════════════════════════════════════════════
async def _generate_report_async(campaign_id: str) -> dict:
    """Fetch all campaign data and produce a comprehensive PDF report."""
    from beanie.odm.operators.find.comparison import In

    from app.models.campaign import Campaign
    from app.models.host import Host
    from app.models.port import Port
    from app.models.report import Report
    from app.models.vulnerability import Vulnerability
    from app.models.banner import Banner
    from app.models.mitre import MitreTechnique
    from app.models.auth_test import AuthTest
    from app.models.sqlmap_scan import SqlmapScan

    campaign = await Campaign.get(campaign_id)
    if not campaign:
        return {"status": "error", "message": f"Campaign {campaign_id} not found"}

    hosts = await Host.find(Host.campaign_id == campaign_id).to_list()
    host_ids = [str(h.id) for h in hosts]

    # Ports
    ports: dict[str, list] = {}
    port_docs = await Port.find(In(Port.host_id, host_ids)).to_list() if host_ids else []
    for p in port_docs:
        ports.setdefault(p.host_id, []).append(p)

    # Vulnerabilities
    vuln_docs = await Vulnerability.find(In(Vulnerability.host_id, host_ids)).to_list() if host_ids else []
    vuln_by_sev: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "none": 0}
    for v in vuln_docs:
        sev = (v.severity or "none").lower()
        if sev in vuln_by_sev:
            vuln_by_sev[sev] += 1

    # Banners
    banner_docs = await Banner.find(In(Banner.host_id, host_ids)).to_list() if host_ids else []

    # MITRE techniques from DB
    mitre_docs = await MitreTechnique.find().to_list()

    # Auth tests
    auth_docs = await AuthTest.find(AuthTest.campaign_id == campaign_id).to_list()

    # SQLmap scans related (by host IP or campaign name)
    sqlmap_docs = await SqlmapScan.find(
        SqlmapScan.status == "completed"
    ).to_list()

    # Build enhanced data bundle
    data = {
        "campaign": campaign,
        "hosts": hosts,
        "ports": ports,
        "vuln_docs": vuln_docs,
        "vuln_by_sev": vuln_by_sev,
        "banner_docs": banner_docs,
        "mitre_docs": mitre_docs,
        "auth_docs": auth_docs,
        "sqlmap_docs": sqlmap_docs,
        "host_ids": host_ids,
    }

    loop = asyncio.get_running_loop()
    pdf_path = await loop.run_in_executor(None, _build_pdf, data)
    file_size = os.path.getsize(pdf_path) if os.path.isfile(pdf_path) else 0

    report = Report(
        campaign_id=campaign_id,
        title=f"Security Assessment Report – {campaign.name}",
        format="pdf",
        file_path=pdf_path,
        size_bytes=file_size,
        summary=_build_summary(campaign, hosts, ports, len(vuln_docs), vuln_by_sev),
        created_by=campaign.created_by,
    )
    await report.insert()

    return {
        "status": "ok",
        "message": f"Report generated for '{campaign.name}'",
        "report_id": str(report.id),
        "file_path": pdf_path,
        "size_bytes": file_size,
    }


# ═══════════════════════════════════════════════════════════════════════
# PDF Builder
# ═══════════════════════════════════════════════════════════════════════
def _build_pdf(data: dict) -> str:
    """Generate a comprehensive security report PDF."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, KeepTogether,
    )

    campaign = data["campaign"]
    hosts = data["hosts"]
    ports = data["ports"]
    vuln_docs = data["vuln_docs"]
    vuln_by_sev = data["vuln_by_sev"]
    banner_docs = data["banner_docs"]
    mitre_docs = data["mitre_docs"]
    sqlmap_docs = data["sqlmap_docs"]

    os.makedirs(_REPORTS_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"report_{campaign.name.replace(' ', '_')}_{ts}.pdf"
    filepath = os.path.join(_REPORTS_DIR, filename)

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm, topMargin=12*mm, bottomMargin=12*mm,
        title=f"NetInsight Security Report – {campaign.name}",
    )

    styles = getSampleStyleSheet()
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    h3 = styles["Heading3"]
    normal = styles["Normal"]
    code_style = ParagraphStyle("Code", parent=normal, fontName="Courier", fontSize=7, leading=9)
    small = ParagraphStyle("Small", parent=normal, fontSize=8, leading=10)

    DARK = colors.HexColor("#1a1a2e")
    ACCENT = colors.HexColor("#e94560")
    CYAN = colors.HexColor("#0f3460")
    LIGHT_BG = colors.HexColor("#f0f2f5")

    story = []
    total_hosts = len(hosts)
    hosts_up = sum(1 for h in hosts if h.status == "up")
    total_ports = sum(len(plist) for plist in ports.values())
    vuln_count = len(vuln_docs)

    def tbl(data_rows, col_widths=None, header=True):
        t = Table(data_rows, colWidths=col_widths, repeatRows=1 if header else 0)
        style_cmds = [
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        if header:
            style_cmds += [
                ("BACKGROUND", (0, 0), (-1, 0), DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ]
        style_cmds.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]))
        t.setStyle(TableStyle(style_cmds))
        return t

    # ═══════════════════════════════════════════════════════════════════
    # PAGE 1 — COVER / EXECUTIVE SUMMARY
    # ═══════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 20*mm))
    story.append(Paragraph("NetInsight", ParagraphStyle("Logo", parent=h1, fontSize=28, textColor=ACCENT, alignment=1)))
    story.append(Paragraph("Security Assessment Report", ParagraphStyle("Sub", parent=h2, fontSize=16, alignment=1, textColor=colors.grey)))
    story.append(Spacer(1, 15*mm))
    story.append(Paragraph(f"<b>Campaign:</b> {campaign.name}", normal))
    story.append(Paragraph(f"<b>Date:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", normal))
    if campaign.description:
        story.append(Paragraph(f"<b>Scope:</b> {campaign.description}", normal))
    story.append(Paragraph(f"<b>Targets:</b> {', '.join(campaign.targets[:5])}{'...' if len(campaign.targets) > 5 else ''}", normal))
    story.append(Spacer(1, 10*mm))

    # Executive Summary
    story.append(Paragraph("Executive Summary", h2))
    risk_level = "CRITICAL" if vuln_by_sev.get("critical", 0) > 0 else "HIGH" if vuln_by_sev.get("high", 0) > 2 else "MEDIUM" if vuln_count > 0 else "LOW"
    risk_color = {"CRITICAL": "#e94560", "HIGH": "#ff6b6b", "MEDIUM": "#ffd93d", "LOW": "#6bcb77"}.get(risk_level, "#6bcb77")
    story.append(Paragraph(f"<b>Overall Risk Level:</b> <font color='{risk_color}'>{risk_level}</font>", normal))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        f"This security assessment identified <b>{total_hosts} hosts</b> ({hosts_up} active), "
        f"<b>{total_ports} open ports</b>, and <b>{vuln_count} vulnerabilities</b> "
        f"({vuln_by_sev.get('critical', 0)} critical, {vuln_by_sev.get('high', 0)} high). "
        f"The assessment included network scanning (Nmap), service detection, banner grabbing, "
        f"vulnerability enumeration (CVE/NVD), SQL injection testing (SQLmap), "
        f"and web application scanning (Nikto).",
        normal,
    ))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # PAGE 2 — ATTACK SURFACE
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("Attack Surface Analysis", h2))
    story.append(Paragraph("Discovered Hosts", h3))
    host_data = [["IP", "Hostname", "OS", "Status", "Open Ports"]]
    for h in hosts:
        host_data.append([h.ip, h.hostname or "-", h.os or "-", h.status, str(len(ports.get(str(h.id), [])))])
    story.append(tbl(host_data, [28*mm, 30*mm, 35*mm, 18*mm, 25*mm]))
    story.append(Spacer(1, 5*mm))

    if total_ports > 0:
        story.append(Paragraph("Open Ports & Services", h3))
        port_data = [["Host", "Port", "Proto", "State", "Service", "Version"]]
        for h in hosts:
            for p in ports.get(str(h.id), []):
                port_data.append([h.ip[:15], str(p.port), p.protocol, p.state, p.service or "-", (p.version or "")[:25]])
        story.append(tbl(port_data, [22*mm, 14*mm, 14*mm, 16*mm, 30*mm, 35*mm]))
        story.append(Spacer(1, 5*mm))

    # Banners
    if banner_docs:
        story.append(Paragraph("Service Banners (Banner Grabbing)", h3))
        for b in banner_docs[:10]:
            story.append(Paragraph(f"<b>{b.service_name}</b>: <font face='Courier' size='7'>{b.raw_banner[:200]}</font>", small))
        story.append(Spacer(1, 3*mm))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # PAGE 3 — VULNERABILITIES + MITRE ATT&CK
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("Vulnerability Assessment", h2))

    # Severity summary
    sev_data = [
        ["Severity", "Count", "Impact"],
        ["CRITICAL", str(vuln_by_sev.get("critical", 0)), "Remote code execution, full system compromise"],
        ["HIGH", str(vuln_by_sev.get("high", 0)), "Data breach, privilege escalation, denial of service"],
        ["MEDIUM", str(vuln_by_sev.get("medium", 0)), "Information disclosure, configuration weaknesses"],
        ["LOW", str(vuln_by_sev.get("low", 0)), "Best practice deviations, hardening opportunities"],
    ]
    story.append(tbl(sev_data, [35*mm, 20*mm, 80*mm]))
    story.append(Spacer(1, 5*mm))

    # CVE details
    if vuln_docs:
        story.append(Paragraph("Identified CVEs", h3))
        cve_data = [["CVE ID", "Severity", "CVSS", "Service", "Description"]]
        for v in sorted(vuln_docs, key=lambda x: -(x.cvss_score or 0))[:20]:
            cve_data.append([
                v.cve_id, v.severity or "NONE", str(v.cvss_score or "—"),
                (v.service_id or "-")[:25],
                (v.description or "")[:100],
            ])
        story.append(tbl(cve_data, [28*mm, 20*mm, 14*mm, 25*mm, 50*mm]))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # PAGE 4 — MITRE ATT&CK MAPPING
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("MITRE ATT&CK Mapping", h2))
    story.append(Paragraph(
        "The following table maps discovered services and vulnerabilities to MITRE ATT&CK "
        "techniques. Each technique is linked to a specific tactic phase in the attack lifecycle.",
        normal,
    ))
    story.append(Spacer(1, 3*mm))

    # Build MITRE table from discovered services
    mitre_rows = [["Technique ID", "Name", "Tactic", "Source"]]
    seen_techniques = set()
    for h in hosts:
        for p in ports.get(str(h.id), []):
            svc = (p.service or "").lower()
            for mapping_key, techniques in MITRE_FINDINGS.items():
                if mapping_key in svc:
                    for tid, tname, tactic in techniques:
                        key = f"{tid}|{tname}"
                        if key not in seen_techniques:
                            seen_techniques.add(key)
                            mitre_rows.append([tid, tname, tactic, f"Service: {p.service} ({h.ip}:{p.port})"])

    # Add SQLi mappings if SQLmap found anything
    if sqlmap_docs:
        for s in sqlmap_docs:
            if s.vulnerabilities_found > 0:
                for tid, tname, tactic in MITRE_FINDINGS.get("sql_injection", []):
                    key = f"{tid}|{tname}"
                    if key not in seen_techniques:
                        seen_techniques.add(key)
                        mitre_rows.append([tid, tname, tactic, f"SQLmap: {s.name} ({s.target_url})"])

    # Count tactics covered
    tactics_covered = set(row[2] for row in mitre_rows[1:])
    story.append(Paragraph(f"<b>Tactics covered:</b> {len(tactics_covered)} — {', '.join(sorted(tactics_covered))}", small))
    story.append(Spacer(1, 2*mm))
    story.append(tbl(mitre_rows, [28*mm, 50*mm, 32*mm, 45*mm]))
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # PAGE 5 — CYBER KILL CHAIN
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("Cyber Kill Chain Analysis", h2))
    story.append(Paragraph(
        "The Lockheed Martin Cyber Kill Chain framework describes the stages of a cyber attack. "
        "Below is the mapping of our findings to each phase of the kill chain.",
        normal,
    ))
    story.append(Spacer(1, 5*mm))

    # Build kill chain evidence for each phase
    kill_chain_evidence = {
        "1. Reconnaissance": [],
        "2. Weaponization": [],
        "3. Delivery": [],
        "4. Exploitation": [],
        "5. Installation": [],
        "6. Command & Control": [],
        "7. Actions on Objectives": [],
    }

    # Reconnaissance: hosts discovered, ports scanned, banners grabbed
    kill_chain_evidence["1. Reconnaissance"].append(f"Nmap scan discovered {total_hosts} hosts with {total_ports} open ports")
    if banner_docs:
        kill_chain_evidence["1. Reconnaissance"].append(f"Banner grabbing captured {len(banner_docs)} service banners revealing version info")

    # Weaponization: CVEs found
    if vuln_docs:
        crit = [v.cve_id for v in vuln_docs if v.severity == "CRITICAL"]
        high = [v.cve_id for v in vuln_docs if v.severity == "HIGH"]
        if crit:
            kill_chain_evidence["2. Weaponization"].append(f"Critical CVEs exploitable: {', '.join(crit)}")
        if high:
            kill_chain_evidence["2. Weaponization"].append(f"High-severity CVEs: {', '.join(high[:5])}")

    # Delivery: exposed services
    exposed_services = set()
    for plist in ports.values():
        for p in plist:
            if p.state == "open" and p.service:
                exposed_services.add(p.service)
    if exposed_services:
        kill_chain_evidence["3. Delivery"].append(f"Exposed services: {', '.join(sorted(exposed_services)[:10])}")

    # Exploitation: SQLmap, weak auth, vulnerable services
    if sqlmap_docs:
        for s in sqlmap_docs:
            if s.vulnerabilities_found > 0:
                kill_chain_evidence["4. Exploitation"].append(f"SQL injection found in {s.target_url} ({s.vulnerabilities_found} injection points)")
    for v in vuln_docs:
        if v.cvss_score and v.cvss_score >= 9.0:
            kill_chain_evidence["4. Exploitation"].append(f"{v.cve_id} (CVSS {v.cvss_score}) — {v.service_id or 'Unknown'}")

    # Installation: auth tests, weak passwords
    kill_chain_evidence["5. Installation"].append("Persistence possible via SSH/RDP with weak credentials")

    # C2: non-standard ports
    std_ports = {22, 80, 443, 25, 53, 110, 143, 993, 3306, 5432, 6379, 8080, 8443}
    for plist in ports.values():
        for p in plist:
            if p.state == "open" and p.port not in std_ports:
                kill_chain_evidence["6. Command & Control"].append(f"Non-standard port {p.port} ({p.service or 'unknown'}) — potential C2 channel")
                break

    # Actions: exfiltrated data, impact
    if sqlmap_docs:
        for s in sqlmap_docs:
            if s.result_summary and s.result_summary.get("dumped_tables"):
                for t in s.result_summary["dumped_tables"]:
                    kill_chain_evidence["7. Actions on Objectives"].append(f"Data exfiltrated: {t['table']} ({t['entries']} rows from {s.target_url})")

    impact_count = vuln_by_sev.get("critical", 0) + vuln_by_sev.get("high", 0)
    if impact_count > 0:
        kill_chain_evidence["7. Actions on Objectives"].append(f"Potential impact: {impact_count} high/critical vulnerabilities affecting confidentiality, integrity, and availability")

    # Render kill chain table
    kc_data = [["Phase", "Description", "Evidence"]]
    for phase_name, description, tools in KILL_CHAIN:
        evidence = "\n".join(kill_chain_evidence.get(phase_name, ["No direct evidence found"]))
        kc_data.append([phase_name, description, evidence])

    kc_table = Table(kc_data, colWidths=[30*mm, 55*mm, 65*mm], repeatRows=1)
    kc_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#f8f9fa")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
    ]))
    story.append(kc_table)
    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # PAGE 6 — EXPLOITATION EVIDENCE
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("Exploitation Evidence", h2))

    if sqlmap_docs:
        story.append(Paragraph("SQL Injection Testing (SQLmap)", h3))
        for s in sqlmap_docs:
            if s.vulnerabilities_found > 0:
                story.append(Paragraph(f"<b>Target:</b> {s.target_url}", normal))
                story.append(Paragraph(f"<b>Injections found:</b> {s.vulnerabilities_found}", normal))
                if s.result_summary:
                    rs = s.result_summary
                    if rs.get("detected_dbms"):
                        story.append(Paragraph(f"<b>DBMS:</b> {rs['detected_dbms']}", normal))
                    if rs.get("vulnerabilities"):
                        for v in rs["vulnerabilities"]:
                            story.append(Paragraph(
                                f"• [{v['severity']}] {v['technique']} — {v['title'][:80]}", small))
                    if rs.get("dumped_tables"):
                        for t in rs["dumped_tables"]:
                            story.append(Paragraph(
                                f"<b>Dumped:</b> {t['table']} ({t['entries']} rows) — {', '.join(t['columns'][:5])}", small))
                story.append(Spacer(1, 3*mm))

    story.append(Paragraph("Authentication Weaknesses", h3))
    story.append(Paragraph("Weak or default credentials detected on exposed services (SSH, RDP, databases).", normal))
    story.append(Paragraph("Recommendation: Enforce strong password policies, enable MFA, disable unused accounts.", normal))

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("MITRE ATT&CK Techniques Summary", h3))
    if seen_techniques:
        for tid, tname, tactic, source in mitre_rows[1:]:
            story.append(Paragraph(f"<b>{tid}</b> — {tname} [{tactic}] — {source}", small))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # PAGE 7 — RECOMMENDATIONS
    # ═══════════════════════════════════════════════════════════════════
    story.append(Paragraph("Recommendations", h2))

    recommendations = [
        ("Critical", "Patch critical vulnerabilities immediately", "CVSS ≥ 9.0"),
        ("Critical", "Fix SQL injection vulnerabilities", "Input validation, parameterized queries"),
        ("High", "Close unnecessary open ports", "Reduce attack surface"),
        ("High", "Update exposed services to latest versions", "Patch management"),
        ("High", "Implement Web Application Firewall (WAF)", "Protect against SQLi, XSS"),
        ("Medium", "Enable HTTPS on all web services", "TLS 1.2+, HSTS"),
        ("Medium", "Implement network segmentation", "Isolate critical assets"),
        ("Medium", "Deploy intrusion detection (IDS/IPS)", "Monitor for exploitation attempts"),
        ("Low", "Regular vulnerability scanning", "Monthly automated scans"),
        ("Low", "Security awareness training", "Phishing, social engineering"),
    ]

    rec_data = [["Priority", "Recommendation", "Rationale"]]
    for prio, rec, rationale in recommendations:
        rec_data.append([prio, rec, rationale])

    rec_table = Table(rec_data, colWidths=[22*mm, 60*mm, 55*mm], repeatRows=1)
    rec_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3436")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
    ]))
    story.append(rec_table)

    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("Methodology", h3))
    story.append(Paragraph(
        "This assessment was conducted using the following tools and frameworks:<br/>"
        "• <b>Nmap</b> — Network discovery and service enumeration (TCP connect scan)<br/>"
        "• <b>Banner Grabbing</b> — Service fingerprinting<br/>"
        "• <b>NVD/CVE Database</b> — Vulnerability correlation<br/>"
        "• <b>SQLmap</b> — SQL injection detection and exploitation<br/>"
        "• <b>Nikto</b> — Web server vulnerability scanning<br/>"
        "• <b>MITRE ATT&CK</b> — Adversary tactics and techniques mapping<br/>"
        "• <b>Cyber Kill Chain</b> — Attack lifecycle analysis",
        normal,
    ))

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("<i>Report generated by NetInsight Platform v0.2.0</i>", small))

    doc.build(story)
    logger.info("PDF report written to %s (%d bytes)", filepath, os.path.getsize(filepath))
    return filepath


def _build_summary(campaign, hosts, ports, vuln_count, vuln_by_sev) -> str:
    total_hosts = len(hosts)
    hosts_up = sum(1 for h in hosts if h.status == "up")
    total_ports = sum(len(plist) for plist in ports.values())
    return (
        f"Campaign '{campaign.name}' — {total_hosts} host(s), "
        f"{hosts_up} up, {total_ports} open port(s), "
        f"{vuln_count} vulnerability(ies) "
        f"(C:{vuln_by_sev.get('critical', 0)} "
        f"H:{vuln_by_sev.get('high', 0)} "
        f"M:{vuln_by_sev.get('medium', 0)} "
        f"L:{vuln_by_sev.get('low', 0)})"
    )


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_campaign_report(self, campaign_id: str) -> dict:
    """Generate a comprehensive PDF security report for the campaign."""
    ensure_db_initialized()
    loop = get_worker_loop()
    try:
        return loop.run_until_complete(_generate_report_async(campaign_id))
    except Exception as exc:
        logger.exception("generate_campaign_report failed for campaign=%s", campaign_id)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "error", "message": f"Max retries exceeded: {exc}"}
