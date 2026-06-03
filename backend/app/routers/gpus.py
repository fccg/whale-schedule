from fastapi import APIRouter, HTTPException, Depends, Query
from app.middleware.auth import require_auth
from app.models.gpu_offering import seed_mock_offerings, get_gpu_offerings as db_get_offerings, get_gpu_offering

router = APIRouter(prefix="/api/gpus", tags=["gpus"])


@router.get("")
async def list_gpus(
    family: str | None = Query(None),
    provider: str | None = Query(None),
    min_price: float | None = Query(None),
    max_price: float | None = Query(None),
    _payload: dict = Depends(require_auth),
):
    await seed_mock_offerings()
    offerings = await db_get_offerings(
        family=family, provider=provider,
        min_price=min_price, max_price=max_price,
        available_only=True,
    )
    return {"gpus": offerings}


@router.get("/{offering_id}")
async def gpu_detail(offering_id: str, _payload: dict = Depends(require_auth)):
    offering = await get_gpu_offering(offering_id)
    if offering is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "GPU offering not found"})
    return offering
