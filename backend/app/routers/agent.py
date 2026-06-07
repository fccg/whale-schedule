import logging
from fastapi import APIRouter, HTTPException
from app.models.instance import get_instance, update_heartbeat, update_instance_status
from app.services.agent_service import handle_heartbeat

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/heartbeat")
async def heartbeat(payload: dict):
    agent_token = payload.get("agent_token")
    instance_id = payload.get("instance_id")
    if not agent_token or not instance_id:
        raise HTTPException(status_code=400, detail={
            "error": "VALIDATION",
            "message": "agent_token and instance_id required",
        })
    instance = await get_instance(instance_id)
    if instance is None or instance["agent_token"] != agent_token:
        raise HTTPException(status_code=403, detail={
            "error": "FORBIDDEN",
            "message": "Invalid agent token",
        })
    has_metrics = any(k in payload for k in ("cpu_percent", "gpus"))
    has_bootstrap = "bootstrap_status" in payload
    logger.debug("Heartbeat received: instance=%s bootstrap=%s metrics=%s",
                 instance_id, has_bootstrap, has_metrics)
    await handle_heartbeat(instance_id, payload)
    return {"status": "ok"}


@router.post("/health-check")
async def health_check_report(payload: dict):
    """Accept health check results from instance agent."""
    agent_token = payload.get("agent_token")
    instance_id = payload.get("instance_id")
    if not agent_token or not instance_id:
        raise HTTPException(status_code=400, detail={
            "error": "VALIDATION",
            "message": "agent_token and instance_id required",
        })
    instance = await get_instance(instance_id)
    if instance is None or instance["agent_token"] != agent_token:
        raise HTTPException(status_code=403, detail={
            "error": "FORBIDDEN",
            "message": "Invalid agent token",
        })

    checks = payload.get("checks", [])
    failed = payload.get("failed", 0)
    overall = payload.get("overall", "unknown")

    if overall == "pass":
        await update_heartbeat(instance_id)
        if instance["status"] == "testing":
            await update_instance_status(instance_id, status="ready", last_error=None)
    elif overall == "partial_fail":
        await update_heartbeat(instance_id)
        failed_names = [c["name"] for c in checks if c.get("status") == "fail"]
        if instance["status"] == "testing":
            await update_instance_status(
                instance_id,
                status="ready",
                last_error=f"Health check partial: {', '.join(failed_names)}" if failed_names else None,
            )

    return {"status": "ok", "checks_received": len(checks)}
