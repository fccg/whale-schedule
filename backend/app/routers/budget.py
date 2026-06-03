from fastapi import APIRouter, Depends, Request
from app.middleware.auth import require_auth
from app.services.budget_service import get_remaining_budget
from app.config import DEFAULT_BUDGET

router = APIRouter(prefix="/api/budget", tags=["budget"])


@router.get("")
async def budget_status(request: Request, _payload: dict = Depends(require_auth)):
    remaining = await get_remaining_budget(request.state.user_id)
    return {
        "total": DEFAULT_BUDGET,
        "spent": round(DEFAULT_BUDGET - remaining, 2),
        "remaining": round(remaining, 2),
    }
