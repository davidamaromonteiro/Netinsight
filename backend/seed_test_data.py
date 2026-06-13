"""
Seed test data into MongoDB for NetInsight demo.
Run: docker exec netinsight-backend python seed_test_data.py
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

# Ensure we're in the right directory
sys.path.insert(0, "/app")

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings
from app.core.db import DOCUMENT_MODELS
from app.models.campaign import Campaign, CampaignStatus
from app.models.host import Host
from app.models.port import Port
from app.models.user import User
from app.models.vulnerability import Vulnerability
from app.models.mitre import MitreTechnique
from app.models.auth_test import AuthTest, AuthTestResult
from app.models.report import Report

settings = get_settings()


async def seed():
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB_NAME]
    await init_beanie(database=db, document_models=DOCUMENT_MODELS)

    now = datetime.now(timezone.utc)

    # ── Create default admin user ────────────────────────────
    from app.core.security import hash_password
    existing = await User.find_one(User.email == "admin@netinsight.io")
    if not existing:
        admin = User(
            email="admin@netinsight.io",
            hashed_password=hash_password("Admin123!"),
            full_name="Admin NetInsight",
            role="admin",
        )
        await admin.insert()
        print(f"  Admin user created: admin@netinsight.io")
    else:
        print(f"  Admin user already exists")

    # ── Campaign 1: Scan réseau interne ──────────────────────────
    c1 = Campaign(
        name="Scan réseau interne",
        description="Audit du réseau interne 192.168.1.0/24",
        targets=["192.168.1.1", "192.168.1.10", "192.168.1.20"],
        scan_params={"ports": "1-1000", "timing": 4},
        status=CampaignStatus.COMPLETED,
        created_by="admin@netinsight.io",
        started_at=now - timedelta(hours=2),
        completed_at=now - timedelta(hours=1, minutes=30),
    )
    await c1.insert()
    print(f"  Campaign: {c1.name} ({c1.id})")

    # ── Campaign 2: Scan DMZ ────────────────────────────────────
    c2 = Campaign(
        name="Scan zone DMZ",
        description="Scan des serveurs exposés en DMZ",
        targets=["10.0.0.5", "10.0.0.10", "10.0.0.15"],
        scan_params={"ports": "1-65535", "timing": 3},
        status=CampaignStatus.COMPLETED,
        created_by="admin@netinsight.io",
        started_at=now - timedelta(days=1),
        completed_at=now - timedelta(hours=23),
    )
    await c2.insert()
    print(f"  Campaign: {c2.name} ({c2.id})")

    # ── Campaign 3: Pending ─────────────────────────────────────
    c3 = Campaign(
        name="Audit serveurs web",
        description="Scan des serveurs web de production",
        targets=["app.example.com", "api.example.com", "cdn.example.com"],
        scan_params={},
        status=CampaignStatus.PENDING,
        created_by="admin@netinsight.io",
    )
    await c3.insert()
    print(f"  Campaign: {c3.name} ({c3.id})")

    # ── Hosts ─────────────────────────────────────────────────────
    hosts_data = [
        {
            "ip": "192.168.1.1",
            "hostname": "gateway.internal.lan",
            "os": "Linux 5.15 (Ubuntu 22.04)",
            "os_accuracy": 95,
            "mac_address": "AA:BB:CC:DD:EE:01",
            "campaign_id": str(c1.id),
            "status": "up",
            "ports": [
                (22, "tcp", "open", "ssh", "OpenSSH 8.9p1"),
                (80, "tcp", "open", "http", "nginx 1.24.0"),
                (443, "tcp", "open", "https", "nginx 1.24.0"),
                (3306, "tcp", "filtered", "mysql", None),
            ],
        },
        {
            "ip": "192.168.1.10",
            "hostname": "db-server.internal.lan",
            "os": "Linux 5.15 (Ubuntu 22.04)",
            "os_accuracy": 92,
            "mac_address": "AA:BB:CC:DD:EE:02",
            "campaign_id": str(c1.id),
            "status": "up",
            "ports": [
                (22, "tcp", "open", "ssh", "OpenSSH 8.9p1"),
                (5432, "tcp", "open", "postgresql", "PostgreSQL 15.3"),
                (6379, "tcp", "open", "redis", "Redis 7.0"),
            ],
        },
        {
            "ip": "192.168.1.20",
            "hostname": "workstation-20.internal.lan",
            "os": "Windows 10",
            "os_accuracy": 88,
            "mac_address": "AA:BB:CC:DD:EE:03",
            "campaign_id": str(c1.id),
            "status": "up",
            "ports": [
                (135, "tcp", "open", "msrpc", "Microsoft Windows RPC"),
                (139, "tcp", "open", "netbios-ssn", None),
                (445, "tcp", "open", "microsoft-ds", "Windows 10"),
                (3389, "tcp", "open", "ms-wbt-server", "Microsoft Terminal Services"),
            ],
        },
        {
            "ip": "10.0.0.5",
            "hostname": "web-dmz.example.com",
            "os": "Linux 6.1 (Debian 12)",
            "os_accuracy": 96,
            "campaign_id": str(c2.id),
            "status": "up",
            "ports": [
                (22, "tcp", "filtered", "ssh", None),
                (80, "tcp", "open", "http", "Apache 2.4.57"),
                (443, "tcp", "open", "https", "Apache 2.4.57"),
                (8080, "tcp", "open", "http-proxy", "Apache Tomcat 10"),
            ],
        },
        {
            "ip": "10.0.0.10",
            "hostname": "mail-dmz.example.com",
            "os": "Linux 6.1 (Debian 12)",
            "os_accuracy": 93,
            "campaign_id": str(c2.id),
            "status": "up",
            "ports": [
                (25, "tcp", "open", "smtp", "Postfix 3.7"),
                (110, "tcp", "open", "pop3", "Dovecot 2.3"),
                (143, "tcp", "open", "imap", "Dovecot 2.3"),
                (587, "tcp", "open", "smtp", "Postfix 3.7"),
                (993, "tcp", "open", "imaps", "Dovecot 2.3"),
            ],
        },
    ]

    for hd in hosts_data:
        host = Host(
            ip=hd["ip"],
            hostname=hd.get("hostname"),
            os=hd.get("os"),
            os_accuracy=hd.get("os_accuracy", 0),
            mac_address=hd.get("mac_address"),
            campaign_id=hd["campaign_id"],
            status=hd["status"],
            last_seen=now - timedelta(hours=1),
        )
        await host.insert()

        for port_num, proto, state, svc, version in hd["ports"]:
            port = Port(
                host_id=str(host.id),
                port=port_num,
                protocol=proto,
                state=state,
                service=svc,
                version=version,
                discovered_at=now - timedelta(hours=1),
            )
            await port.insert()

        print(f"  Host: {hd['ip']} ({host.id}) - {len(hd['ports'])} ports")

    # ── Vulnerabilities (CVE) ──────────────────────────────────────
    vuln_data = [
        {
            "cve_id": "CVE-2023-44487",
            "host_id": str((await Host.find_one(Host.ip == "192.168.1.1")).id),
            "severity": "HIGH",
            "cvss_score": 7.5,
            "cvss_version": "3.1",
            "description": "The HTTP/2 protocol allows a denial of service (server resource consumption) because request cancellation can reset many streams quickly, as exploited in the wild in August through October 2023 (Rapid Reset Attack).",
            "service_name": "nginx",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2023-44487"],
        },
        {
            "cve_id": "CVE-2024-10914",
            "host_id": str((await Host.find_one(Host.ip == "192.168.1.10")).id),
            "severity": "CRITICAL",
            "cvss_score": 9.8,
            "cvss_version": "3.1",
            "description": "A command injection vulnerability in PostgreSQL via the `COPY ... FROM PROGRAM` feature allows authenticated users to execute arbitrary OS commands.",
            "service_name": "postgresql",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2024-10914"],
        },
        {
            "cve_id": "CVE-2023-45145",
            "host_id": str((await Host.find_one(Host.ip == "192.168.1.10")).id),
            "severity": "MEDIUM",
            "cvss_score": 5.9,
            "cvss_version": "3.1",
            "description": "Redis is an in-memory database that persists on disk. On startup, Redis begins listening on a Unix socket before adjusting its permissions to the user-provided configuration. If a permissive umask(2) is used, this creates a race condition that enables, during a short period of time, another process to establish an otherwise unauthorized connection.",
            "service_name": "redis",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2023-45145"],
        },
        {
            "cve_id": "CVE-2024-21318",
            "host_id": str((await Host.find_one(Host.ip == "192.168.1.20")).id),
            "severity": "HIGH",
            "cvss_score": 8.8,
            "cvss_version": "3.1",
            "description": "Microsoft WDAC OLE DB Provider for SQL Server Remote Code Execution Vulnerability.",
            "service_name": "msrpc",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2024-21318"],
        },
        {
            "cve_id": "CVE-2019-0708",
            "host_id": str((await Host.find_one(Host.ip == "192.168.1.20")).id),
            "severity": "CRITICAL",
            "cvss_score": 9.8,
            "cvss_version": "3.1",
            "description": "A remote code execution vulnerability exists in Remote Desktop Services formerly known as Terminal Services when an unauthenticated attacker connects to the target system using RDP and sends specially crafted requests (BlueKeep).",
            "service_name": "ms-wbt-server",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2019-0708"],
        },
        {
            "cve_id": "CVE-2023-25690",
            "host_id": str((await Host.find_one(Host.ip == "10.0.0.5")).id),
            "severity": "HIGH",
            "cvss_score": 7.5,
            "cvss_version": "3.1",
            "description": "Some mod_proxy configurations on Apache HTTP Server versions 2.4.0 through 2.4.55 allow a HTTP Request Smuggling attack. Configurations are affected when mod_proxy is enabled along with some form of RewriteRule or ProxyPassMatch.",
            "service_name": "apache",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2023-25690"],
        },
        {
            "cve_id": "CVE-2023-51764",
            "host_id": str((await Host.find_one(Host.ip == "10.0.0.10")).id),
            "severity": "MEDIUM",
            "cvss_score": 5.3,
            "cvss_version": "3.1",
            "description": "Postfix through 3.8.5 allows SMTP smuggling unless configured with smtpd_data_restrictions or smtpd_discard_ehlo_keywords.",
            "service_name": "postfix",
            "references": ["https://nvd.nist.gov/vuln/detail/CVE-2023-51764"],
        },
    ]

    for vd in vuln_data:
        vuln = Vulnerability(
            cve_id=vd["cve_id"],
            host_id=vd["host_id"],
            campaign_id=str((await Host.get(vd["host_id"])).campaign_id),
            service_id=f"svc-{vd['service_name']}-{vd['host_id'][:8]}",
            severity=vd["severity"],
            cvss_score=vd["cvss_score"],
            cvss_version=vd["cvss_version"],
            description=vd["description"],
            service_name=vd["service_name"],
            references=vd.get("references", []),
            discovered_at=now - timedelta(hours=1),
        )
        await vuln.insert()
        print(f"  Vuln: {vd['cve_id']} ({vd['severity']})")

    # ── MITRE ATT&CK techniques ───────────────────────────────────
    mitre_data = [
        ("T1190", "Exploit Public-Facing Application", "Initial Access", "TA0001"),
        ("T1110", "Brute Force", "Credential Access", "TA0006"),
        ("T1078", "Valid Accounts", "Defense Evasion", "TA0005"),
        ("T1021", "Remote Services", "Lateral Movement", "TA0008"),
        ("T1569", "System Services", "Execution", "TA0002"),
        ("T1505", "Server Software Component", "Persistence", "TA0003"),
        ("T1046", "Network Service Scanning", "Discovery", "TA0007"),
        ("T1210", "Exploitation of Remote Services", "Lateral Movement", "TA0008"),
    ]

    for tid, tname, tactic, tactic_id in mitre_data:
        tech = MitreTechnique(
            technique_id=tid,
            technique_name=tname,
            tactic=tactic,
            tactic_id=tactic_id,
            description=f"MITRE ATT&CK technique {tid}: {tname}",
            url=f"https://attack.mitre.org/techniques/{tid}/",
            mapped_at=now,
        )
        await tech.insert()
        print(f"  MITRE: {tid} — {tname} ({tactic})")

    # ── Auth tests ─────────────────────────────────────────────────
    auth_data = [
        ("192.168.1.1", 22, "ssh", "root", AuthTestResult.FAILED),
        ("192.168.1.1", 22, "ssh", "admin", AuthTestResult.SUCCESS),
        ("192.168.1.10", 5432, "postgresql", "postgres", AuthTestResult.SUCCESS),
        ("192.168.1.10", 6379, "redis", "", AuthTestResult.SUCCESS),
        ("192.168.1.20", 445, "smb", "Administrator", AuthTestResult.FAILED),
        ("10.0.0.5", 8080, "tomcat", "admin", AuthTestResult.SUCCESS),
    ]

    for ip, port_num, svc_name, username, result in auth_data:
        host = await Host.find_one(Host.ip == ip)
        if host:
            auth = AuthTest(
                campaign_id=host.campaign_id,
                host_id=str(host.id),
                port_id=str(port_num),
                service_name=svc_name,
                username=username,
                result=result,
                tested_at=now - timedelta(minutes=30),
            )
            await auth.insert()
    print(f"  AuthTests: {len(auth_data)} entries")

    print("\n✅ Test data seeded successfully!")
    print(f"   {await Campaign.find().count()} campaigns")
    print(f"   {await Host.find().count()} hosts")
    print(f"   {await Port.find().count()} ports")
    print(f"   {await Vulnerability.find().count()} vulnerabilities")
    print(f"   {await MitreTechnique.find().count()} MITRE techniques")
    print(f"   {await AuthTest.find().count()} auth tests")


if __name__ == "__main__":
    asyncio.run(seed())
