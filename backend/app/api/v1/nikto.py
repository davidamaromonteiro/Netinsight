"""Nikto web scanner endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import require_auth, require_analyst
from app.models.nikto_scan import NiktoScan, NiktoScanStatus
from app.models.user import User
from app.schemas.nikto import NiktoScanCreate, NiktoScanResponse
from app.services.audit_service import log_action

router = APIRouter(prefix="/nikto", tags=["Nikto"])


def _scan_to_response(s: NiktoScan) -> NiktoScanResponse:
    return NiktoScanResponse(
        id=str(s.id),
        name=s.name,
        description=s.description,
        target_url=s.target_url,
        target_host=s.target_host,
        target_port=s.target_port,
        use_ssl=s.use_ssl,
        status=s.status.value,
        nikto_params=s.nikto_params,
        created_by=s.created_by,
        created_at=s.created_at,
        started_at=s.started_at,
        completed_at=s.completed_at,
        vulnerabilities_found=s.vulnerabilities_found,
        result_summary=s.result_summary,
        raw_output=s.raw_output,
    )


@router.post("/", response_model=NiktoScanResponse, status_code=status.HTTP_201_CREATED)
async def create_nikto_scan(
    payload: NiktoScanCreate,
    user: User = Depends(require_analyst),
):
    """Create a new Nikto web scan."""
    scan = NiktoScan(
        name=payload.name,
        description=payload.description,
        target_url=payload.target_url,
        target_host=payload.target_host,
        target_port=payload.target_port,
        use_ssl=payload.use_ssl,
        nikto_params=payload.nikto_params,
        created_by=user.email,
    )
    await scan.insert()
    log_action(user.email, "nikto_scan_created", "nikto", str(scan.id), {"name": scan.name, "target": scan.target_url})
    return _scan_to_response(scan)


@router.get("/", response_model=list[NiktoScanResponse])
async def list_nikto_scans(
    status_filter: Optional[str] = Query(None, alias="status"),
    user: User = Depends(require_auth),
):
    """List all Nikto scans."""
    query = {}
    if status_filter:
        query["status"] = status_filter
    scans = await NiktoScan.find(query).sort(-NiktoScan.created_at).to_list()
    return [_scan_to_response(s) for s in scans]


@router.get("/{scan_id}", response_model=NiktoScanResponse)
async def get_nikto_scan(
    scan_id: str,
    user: User = Depends(require_auth),
):
    """Get a single Nikto scan by ID."""
    scan = await NiktoScan.get(scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _scan_to_response(scan)


@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_nikto_scan(
    scan_id: str,
    user: User = Depends(require_analyst),
):
    """Delete a Nikto scan."""
    scan = await NiktoScan.get(scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await scan.delete()
    log_action(user.email, "nikto_scan_deleted", "nikto", scan_id)


@router.post("/{scan_id}/scan", status_code=status.HTTP_202_ACCEPTED)
async def trigger_scan(
    scan_id: str,
    user: User = Depends(require_analyst),
):
    """Start a Nikto scan."""
    scan = await NiktoScan.get(scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if scan.status not in (NiktoScanStatus.PENDING, NiktoScanStatus.FAILED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Scan must be pending or failed to start")

    from app.tasks.nikto import run_nikto_scan

    task = run_nikto_scan.delay(scan_id)
    log_action(user.email, "nikto_scan_triggered", "nikto", scan_id)

    return {"status": "accepted", "task_id": task.id, "scan_id": scan_id}
