from fastapi import APIRouter, HTTPException, Depends, Query
from app.middleware.auth import require_auth
from app.services.market_service import get_launch_payload, get_market_offering, list_market_offerings
from fastapi import Request

router = APIRouter(prefix="/api/gpus", tags=["gpus"])


@router.get("")
async def list_gpus(
    request: Request,
    search: str | None = Query(None),
    family: str | None = Query(None),
    model: str | None = Query(None),
    provider: str | None = Query(None),
    region: str | None = Query(None),
    min_price: float | None = Query(None),
    max_price: float | None = Query(None),
    _payload: dict = Depends(require_auth),
):
    _ = request
    payload = await list_market_offerings(
        search=search,
        family=family, model=model, provider=provider, region=region,
        min_price=min_price, max_price=max_price,
        available_only=True,
    )
    return {
        **payload,
        "gpus": payload["items"],
    }


@router.get("/{offering_id}")
async def gpu_detail(offering_id: str, _payload: dict = Depends(require_auth)):
    offering = await get_market_offering(offering_id)
    if offering is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "GPU offering not found"})
    return offering


@router.get("/{offering_id}/launch")
async def launch_detail(offering_id: str, _payload: dict = Depends(require_auth)):
    payload = await get_launch_payload(offering_id)
    if payload is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "GPU offering not found"})
    return payload
