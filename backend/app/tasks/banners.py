"""
Celery tasks for banner grabbing on open ports.
"""
import asyncio
import logging
from datetime import datetime, timezone

from app.tasks import celery_app, ensure_db_initialized, get_worker_loop

logger = logging.getLogger(__name__)


async def _grab_banner_async(host_id: str) -> dict:
    """Grab banners from all open ports on a host."""
    from app.models.host import Host
    from app.models.port import Port
    from app.models.banner import Banner

    host = await Host.get(host_id)
    if not host:
        return {"status": "error", "message": f"Host {host_id} not found"}

    ports = await Port.find(
        Port.host_id == host_id,
        Port.state == "open"
    ).to_list()

    if not ports:
        return {"status": "ok", "message": "No open ports to grab banners from", "banners": 0}

    banners_grabbed = 0
    for port in ports:
        try:
            banner_text = await _grab_single_banner(host.ip, port.port, port.protocol)
            if banner_text:
                banner = Banner(
                    host_id=host_id,
                    port_id=str(port.id),
                    service_name=port.service or "unknown",
                    raw_banner=banner_text[:2000],
                    parsed_info=_parse_banner(banner_text, port.service),
                )
                await banner.insert()
                banners_grabbed += 1
                logger.info("Banner grabbed: %s:%d (%s)", host.ip, port.port, port.service)
        except Exception as exc:
            logger.warning("Banner grab failed for %s:%d: %s", host.ip, port.port, exc)

    return {
        "status": "ok",
        "message": f"Grabbed {banners_grabbed} banners from {len(ports)} ports",
        "banners_grabbed": banners_grabbed,
        "total_ports": len(ports),
    }


async def _grab_single_banner(ip: str, port: int, protocol: str) -> str | None:
    """Grab banner from a single port."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=5.0
        )
        try:
            # Send a probe based on protocol
            if protocol == "tcp":
                writer.write(b"\r\n")
                await writer.drain()

            banner = await asyncio.wait_for(reader.read(4096), timeout=3.0)
            return banner.decode("utf-8", errors="replace").strip()
        finally:
            writer.close()
            await writer.wait_closed()
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        return None


def _parse_banner(banner_text: str, service_name: str | None) -> dict:
    """Parse banner text to extract version and other info."""
    import re
    info: dict = {}

    # Common patterns
    if "SSH" in banner_text or service_name == "ssh":
        ver = re.search(r"SSH-\d+\.\d+-(\S+)", banner_text)
        if ver:
            info["server"] = ver.group(1)
    elif "HTTP" in banner_text or service_name in ("http", "https"):
        server = re.search(r"Server:\s*(\S+)", banner_text)
        if server:
            info["server"] = server.group(1)
    elif "MySQL" in banner_text or service_name == "mysql":
        ver = re.search(r"(\d+\.\d+\.\d+)", banner_text)
        if ver:
            info["version"] = ver.group(1)
    elif "PostgreSQL" in banner_text or service_name == "postgresql":
        info["type"] = "PostgreSQL"

    if banner_text and not info:
        info["raw_length"] = len(banner_text)

    return info


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def grab_host_banners(self, host_id: str) -> dict:
    """Grab banners from all open ports on a host."""
    ensure_db_initialized()
    loop = get_worker_loop()
    try:
        return loop.run_until_complete(_grab_banner_async(host_id))
    except Exception as exc:
        logger.exception("grab_host_banners failed for host_id=%s", host_id)
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "error", "message": str(exc)}
