"""Sqlmap scan management endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
import csv
import io
import json

from app.api.deps import require_auth, require_analyst
from app.models.sqlmap_scan import SqlmapScan, SqlmapScanStatus
from app.models.user import User
from app.schemas.sqlmap import SqlmapScanCreate, SqlmapScanResponse
from app.services.audit_service import log_action

router = APIRouter(prefix="/sqlmap", tags=["Sqlmap"])


@router.post("/", response_model=SqlmapScanResponse, status_code=status.HTTP_201_CREATED)
async def create_sqlmap_scan(
    payload: SqlmapScanCreate,
    user: User = Depends(require_analyst),
):
    """Create a new sqlmap scan."""
    from app.core.validators import validate_sqlmap_args

    raw_args = payload.sqlmap_params.get("sqlmap_args", "--batch")
    validate_sqlmap_args(raw_args)

    scan = SqlmapScan(
        name=payload.name,
        description=payload.description,
        target_url=payload.target_url,
        sqlmap_params=payload.sqlmap_params,
        created_by=user.email,
    )
    await scan.insert()
    log_action(user.email, "sqlmap_scan_created", "sqlmap", str(scan.id), {"name": scan.name, "target": scan.target_url})
    return _scan_to_response(scan)


@router.get("/", response_model=list[SqlmapScanResponse])
async def list_sqlmap_scans(
    status_filter: Optional[str] = Query(None, alias="status"),
    user: User = Depends(require_auth),
):
    """List all sqlmap scans, optionally filtered by status."""
    query = {}
    if status_filter:
        query["status"] = status_filter
    scans = await SqlmapScan.find(query).sort(-SqlmapScan.created_at).to_list()
    return [_scan_to_response(s) for s in scans]


@router.get("/{scan_id}", response_model=SqlmapScanResponse)
async def get_sqlmap_scan(
    scan_id: str,
    user: User = Depends(require_auth),
):
    """Get a single sqlmap scan by ID."""
    scan = await SqlmapScan.get(scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _scan_to_response(scan)


@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sqlmap_scan(
    scan_id: str,
    user: User = Depends(require_analyst),
):
    """Delete a sqlmap scan."""
    scan = await SqlmapScan.get(scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await scan.delete()
    log_action(user.email, "sqlmap_scan_deleted", "sqlmap", scan_id)
    return None


@router.post("/{scan_id}/scan", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scan(
    scan_id: str,
    user: User = Depends(require_analyst),
):
    """Start a sqlmap scan."""
    from app.services.sqlmap_service import trigger_sqlmap_scan

    result = await trigger_sqlmap_scan(scan_id, user.email)
    log_action(user.email, "sqlmap_scan_triggered", "sqlmap", scan_id)
    return result


@router.get("/{scan_id}/export")
async def export_scan(
    scan_id: str,
    fmt: str = Query("json", alias="format"),
    user: User = Depends(require_auth),
):
    """Export a sqlmap scan result as JSON or CSV."""
    scan = await SqlmapScan.get(scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    data = {
        "id": str(scan.id),
        "name": scan.name,
        "target_url": scan.target_url,
        "status": scan.status.value,
        "vulnerabilities_found": scan.vulnerabilities_found,
        "result_summary": scan.result_summary or {},
        "started_at": scan.started_at.isoformat() if scan.started_at else None,
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
    }

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Field", "Value"])
        for k, v in data.items():
            if isinstance(v, dict):
                for dk, dv in v.items():
                    writer.writerow([f"{k}.{dk}", dv])
            else:
                writer.writerow([k, v])
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=sqlmap_{scan_id}.csv"},
        )

    return data


def _scan_to_response(s: SqlmapScan) -> SqlmapScanResponse:
    return SqlmapScanResponse(
        id=str(s.id),
        name=s.name,
        description=s.description,
        target_url=s.target_url,
        status=s.status.value,
        sqlmap_params=s.sqlmap_params,
        created_by=s.created_by,
        created_at=s.created_at,
        started_at=s.started_at,
        completed_at=s.completed_at,
        result_summary=s.result_summary,
        vulnerabilities_found=s.vulnerabilities_found,
        raw_output=s.raw_output,
    )
