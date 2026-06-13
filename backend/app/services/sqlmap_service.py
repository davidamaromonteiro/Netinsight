"""
Sqlmap orchestration service.
Wraps Celery task dispatching with business validation.
"""

import logging

from fastapi import HTTPException, status

from app.models.sqlmap_scan import SqlmapScan, SqlmapScanStatus

logger = logging.getLogger(__name__)


async def trigger_sqlmap_scan(scan_id: str, user_email: str) -> dict:
    """Validate and dispatch a sqlmap scan via Celery.

    Args:
        scan_id: The ID of the sqlmap scan to run.
        user_email: The email of the authenticated user triggering the scan.

    Returns:
        A dict with status, task_id, and scan_id.

    Raises:
        HTTPException: 404 if the scan does not exist,
                       409 if the scan is not in a startable state.
    """
    scan = await SqlmapScan.get(scan_id)
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sqlmap scan {scan_id} not found",
        )

    if scan.status not in (SqlmapScanStatus.PENDING, SqlmapScanStatus.FAILED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scan must be pending or failed to start",
        )

    from app.tasks.sqlmap import run_sqlmap_scan

    task = run_sqlmap_scan.delay(scan_id)

    logger.info(
        "Sqlmap scan triggered by %s: scan_id=%s task_id=%s",
        user_email,
        scan_id,
        task.id,
    )

    return {
        "status": "accepted",
        "task_id": task.id,
        "scan_id": scan_id,
    }
