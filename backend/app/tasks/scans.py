"""
Celery tasks for network scanning.

Provides:
    run_campaign_scan(campaign_id)  – orchestrates a full campaign scan
    scan_host(host_id)              – scans a single host with python-nmap
    _finalize_campaign(campaign_id) – chord callback to update campaign status
"""

import logging
from datetime import datetime, timezone

from celery import chord

from app.tasks import celery_app, ensure_db_initialized, get_worker_loop

logger = logging.getLogger(__name__)


# ======================================================================
# Helper – async core of scan_host
# ======================================================================
async def _scan_host_async(host_id: str) -> dict:
    """Perform an nmap scan against a single host and persist results."""
    from app.models.campaign import Campaign
    from app.models.host import Host
    from app.models.port import Port

    # --- Fetch models ----------------------------------------------------
    host = await Host.get(host_id)
    if not host:
        return {"status": "error", "message": f"Host {host_id} not found"}

    campaign = await Campaign.get(host.campaign_id)
    scan_params: dict = campaign.scan_params if campaign else {}

    # --- Nmap arguments --------------------------------------------------
    # Default: SYN scan + service version detection on top 1000 ports
    from app.core.validators import validate_nmap_args

    raw_args = scan_params.get("nmap_args", "-sT -sV -T4 --open")
    nmap_args = validate_nmap_args(raw_args)

    # Only add host-timeout if not already specified by user
    if "--host-timeout" not in nmap_args:
        from app.core.config import get_settings
        timeout = get_settings().SCAN_TIMEOUT_SECONDS
        nmap_args += f" --host-timeout {timeout}s"

    # --- Import nmap -----------------------------------------------------
    try:
        import nmap
    except ImportError:
        host.status = "error"
        await host.save()
        logger.warning("python-nmap not installed; cannot scan %s", host.ip)
        return {"status": "error", "message": "python-nmap library not available"}

    # --- Run scan --------------------------------------------------------
    try:
        nm = nmap.PortScanner()
        nm.scan(hosts=host.ip, arguments=nmap_args)
    except Exception as exc:
        host.status = "error"
        await host.save()
        logger.error("Nmap scan failed for %s: %s", host.ip, exc)
        return {"status": "error", "message": f"Nmap scan failed: {exc}"}

    # --- Parse results ---------------------------------------------------
    all_hosts = nm.all_hosts()
    if not all_hosts:
        host.status = "down"
        host.last_seen = datetime.now(timezone.utc)
        await host.save()
        logger.info("Host %s is down / no response", host.ip)
        return {"status": "ok", "message": f"Host {host.ip} is down"}

    host_data = nm[all_hosts[0]]
    if host_data.state() != "up":
        host.status = "down"
        host.last_seen = datetime.now(timezone.utc)
        await host.save()
        return {"status": "ok", "message": f"Host {host.ip} state: {host_data.state()}"}

    # --- Update Host document --------------------------------------------
    host.status = "up"
    host.last_seen = datetime.now(timezone.utc)
    if host_data.hostname():
        host.hostname = host_data.hostname()
    addresses = host_data.get("addresses", {})
    if addresses.get("mac"):
        host.mac_address = addresses["mac"]
    os_matches = host_data.get("osmatch", [])
    if os_matches:
        host.os = os_matches[0].get("name", "")
        host.os_accuracy = int(os_matches[0].get("accuracy", 0))
    await host.save()

    # --- Replace old Port documents --------------------------------------
    await Port.find(Port.host_id == host_id).delete()

    open_ports: list[int] = []
    total_ports = 0
    for proto in host_data.all_protocols():
        ports_for_proto: dict = host_data[proto]
        for port_num in sorted(ports_for_proto.keys()):
            info = ports_for_proto[port_num]
            port_state = info.get("state", "unknown")
            port_doc = Port(
                host_id=host_id,
                port=int(port_num),
                protocol=proto,
                state=port_state,
                service=info.get("name"),
                version=info.get("version"),
                extra_info=info.get("product"),
            )
            await port_doc.insert()
            total_ports += 1
            if port_state == "open":
                open_ports.append(int(port_num))

    logger.info(
        "Scanned %s: %d total ports, %d open",
        host.ip, total_ports, len(open_ports),
    )
    return {
        "status": "ok",
        "message": f"Scanned {host.ip}: {len(open_ports)} open / {total_ports} total port(s)",
        "ip": host.ip,
        "open_ports": open_ports,
        "total_ports": total_ports,
    }


# ======================================================================
# Task: scan a single host
# ======================================================================
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def scan_host(self, host_id: str) -> dict:
    """Scan a single host with nmap, persist open ports in MongoDB."""
    ensure_db_initialized()
    loop = get_worker_loop()
    try:
        return loop.run_until_complete(_scan_host_async(host_id))
    except Exception as exc:
        logger.exception("scan_host failed for host_id=%s", host_id)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "error", "message": f"Max retries exceeded: {exc}"}


# ======================================================================
# Helper – async core of run_campaign_scan
# ======================================================================
async def _run_campaign_async(campaign_id: str) -> dict:
    """Create Host documents for each campaign target, return their IDs."""
    from app.models.campaign import Campaign, CampaignStatus
    from app.models.host import Host

    campaign = await Campaign.get(campaign_id)
    if not campaign:
        return {"status": "error", "message": f"Campaign {campaign_id} not found"}

    # Mark as running
    campaign.status = CampaignStatus.RUNNING
    campaign.started_at = datetime.now(timezone.utc)
    await campaign.save()

    # Create/update Host documents for each target
    host_ids: list[str] = []
    for target in campaign.targets:
        host = await Host.find_one(
            Host.ip == target,
            Host.campaign_id == campaign_id,
        )
        if not host:
            host = Host(ip=target, campaign_id=campaign_id, status="pending")
            await host.insert()
        else:
            # Reset status for re-scan
            host.status = "pending"
            await host.save()
        host_ids.append(str(host.id))

    return {"status": "ok", "host_ids": host_ids}


# ======================================================================
# Task: orchestrate a full campaign scan
# ======================================================================
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_campaign_scan(self, campaign_id: str) -> dict:
    """Orchestrate a full campaign scan.

    1. Creates Host documents for every target.
    2. Dispatches scan_host tasks for all hosts in parallel.
    3. A chord callback (_finalize_campaign) updates the campaign status.
    """
    ensure_db_initialized()
    loop = get_worker_loop()

    try:
        result = loop.run_until_complete(_run_campaign_async(campaign_id))
    except Exception as exc:
        logger.exception("run_campaign_scan setup failed for campaign=%s", campaign_id)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "error", "message": f"Max retries exceeded: {exc}"}

    if result.get("status") == "error":
        return result

    host_ids: list[str] = result.get("host_ids", [])

    if not host_ids:
        # No hosts to scan – finalize immediately
        _finalize_campaign.delay(campaign_id)
        return {
            "status": "ok",
            "message": "No hosts to scan; campaign finalised",
        }

    # Dispatch all host scans in parallel, with a chord callback
    header = [scan_host.s(hid) for hid in host_ids]
    callback = _finalize_campaign.s(campaign_id)
    chord(header, callback).delay()

    return {
        "status": "running",
        "message": f"Dispatched {len(host_ids)} host scan(s)",
        "host_ids": host_ids,
    }


# ======================================================================
# Helper – async core of _finalize_campaign
# ======================================================================
async def _finalize_campaign_async(campaign_id: str) -> dict:
    """Update campaign status after all host scans complete."""
    from app.models.campaign import Campaign, CampaignStatus
    from app.models.host import Host

    campaign = await Campaign.get(campaign_id)
    if not campaign:
        return {"status": "error", "message": f"Campaign {campaign_id} not found"}

    # Count hosts by status
    hosts = await Host.find(Host.campaign_id == campaign_id).to_list()
    total = len(hosts)
    up = sum(1 for h in hosts if h.status == "up")
    down = sum(1 for h in hosts if h.status == "down")
    error = sum(1 for h in hosts if h.status == "error")

    if error > 0 and up == 0:
        campaign.status = CampaignStatus.FAILED
    else:
        campaign.status = CampaignStatus.COMPLETED

    campaign.completed_at = datetime.now(timezone.utc)
    await campaign.save()

    # Auto-enrich: MITRE mapping + CVE lookup for UP hosts
    try:
        from app.services.mitre_service import map_host_ports_to_mitre
        for h in hosts:
            if h.status == "up":
                try:
                    await map_host_ports_to_mitre(str(h.id))
                except Exception as exc:
                    logger.warning("MITRE mapping failed for host %s: %s", h.ip, exc)
    except Exception as exc:
        logger.warning("MITRE enrichment skipped: %s", exc)

    logger.info(
        "Campaign %s finalised: total=%d up=%d down=%d error=%d status=%s",
        campaign.name, total, up, down, error, campaign.status.value,
    )
    return {
        "status": "ok",
        "message": f"Campaign {campaign.name} finalised",
        "total_hosts": total,
        "hosts_up": up,
        "hosts_down": down,
        "hosts_error": error,
        "campaign_status": campaign.status.value,
    }


# ======================================================================
# Task: finalise a campaign (chord callback)
# ======================================================================
@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def _finalize_campaign(self, chord_results=None, campaign_id: str = "") -> dict:
    """Callback executed after all host scans in a campaign finish.
    chord_results is passed automatically by Celery chord."""
    # If called as chord callback, chord_results is the list of scan results
    # and campaign_id is passed via .s(campaign_id)
    if campaign_id and chord_results is not None:
        pass  # chord callback mode: chord_results + campaign_id
    
    # If campaign_id is empty, chord_results might be the campaign_id
    if not campaign_id and chord_results and isinstance(chord_results, str):
        campaign_id = chord_results
    
    ensure_db_initialized()
    loop = get_worker_loop()
    try:
        return loop.run_until_complete(_finalize_campaign_async(campaign_id))
    except Exception as exc:
        logger.exception("_finalize_campaign failed for campaign=%s", campaign_id)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "error", "message": f"Max retries exceeded: {exc}"}
