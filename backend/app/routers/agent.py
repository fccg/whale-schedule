from fastapi import APIRouter, HTTPException
from app.models.instance import get_instance, update_heartbeat
from app.services.agent_service import handle_heartbeat

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/heartbeat")
async def heartbeat(payload: dict):
    agent_token = payload.get("agent_token")
    instance_id = payload.get("instance_id")
    if not agent_token or not instance_id:
        raise HTTPException(status_code=400, detail={"error": "VALIDATION", "message": "agent_token and instance_id required"})
    instance = await get_instance(instance_id)
    if instance is None or instance["agent_token"] != agent_token:
        raise HTTPException(status_code=403, detail={"error": "FORBIDDEN", "message": "Invalid agent token"})
    await handle_heartbeat(instance_id, payload)
    return {"status": "ok"}
