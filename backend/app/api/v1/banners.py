"""Banner grabbing endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_auth
from app.models.banner import Banner
from app.models.host import Host
from app.models.user import User
from app.schemas.banner import BannerResponse

router = APIRouter(prefix="/banners", tags=["Banners"])


@router.get("/host/{host_id}", response_model=list[BannerResponse])
async def get_host_banners(
    host_id: str,
    user: User = Depends(require_auth),
):
    """Get all banners grabbed for a host."""
    host = await Host.get(host_id)
    if not host:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host not found")

    banners = await Banner.find(Banner.host_id == host_id).sort(-Banner.grabbed_at).to_list()
    return [
        BannerResponse(
            id=str(b.id),
            host_id=b.host_id,
            port_id=b.port_id,
            service_name=b.service_name,
            raw_banner=b.raw_banner,
            parsed_info=b.parsed_info,
            grabbed_at=b.grabbed_at,
        )
        for b in banners
    ]


@router.post("/host/{host_id}/grab", status_code=status.HTTP_202_ACCEPTED)
async def trigger_banner_grab(
    host_id: str,
    user: User = Depends(require_auth),
):
    """Trigger banner grabbing on all open ports of a host."""
    host = await Host.get(host_id)
    if not host:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Host not found")

    from app.tasks.banners import grab_host_banners

    task = grab_host_banners.delay(host_id)

    return {
        "status": "accepted",
        "task_id": task.id,
        "host_id": host_id,
        "message": "Banner grabbing started",
    }
