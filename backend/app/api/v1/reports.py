"""Report download endpoint."""

import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.deps import require_auth
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    user: User = Depends(require_auth),
):
    """Download a generated report PDF."""
    from app.services.report_service import get_report_filepath

    filepath = await get_report_filepath(report_id)
    if not filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found",
        )

    filename = os.path.basename(filepath)
    return FileResponse(
        path=filepath,
        media_type="application/pdf",
        filename=filename,
    )
