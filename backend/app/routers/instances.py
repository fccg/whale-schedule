import json
import secrets
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from app.middleware.auth import require_auth
from app.models.instance import create_instance, get_instance, get_user_instances, destroy_instance, update_instance_status
from app.models.gpu_offering import get_gpu_offering
from app.models.metric import get_latest_metrics, get_metrics_history
from app.services.instance_service import start_lifecycle_advance
from app.services.budget_service import check_budget, log_budget, get_remaining_budget
from app.providers.mock import MockProvider

router = APIRouter(prefix="/api/instances", tags=["instances"])


class CreateInstanceRequest(BaseModel):
    gpu_offering_id: str
    template: str = "nvidia/pytorch:26.03-py3"
    disk_gb: int = 200
    duration_h: int = 1


@router.post("")
async def create(request: Request, body: CreateInstanceRequest, _payload: dict = Depends(require_auth)):
    offering = await get_gpu_offering(body.gpu_offering_id)
    if offering is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "GPU offering not found"})
    estimated_total = offering["price_per_hour"] * body.duration_h
    if not await check_budget(request.state.user_id, estimated_total):
        raise HTTPException(status_code=422, detail={
            "error": "BUDGET_EXCEEDED",
            "message": f"Estimated cost ¥{estimated_total:.2f} exceeds remaining budget",
        })
    config = {
        "template": body.template,
        "disk_gb": body.disk_gb,
        "duration_h": body.duration_h,
    }
    agent_token = secrets.token_hex(16)
    provider = MockProvider()
    try:
        provider_result = await provider.create_instance(body.gpu_offering_id, config)
        provider_instance_id = provider_result["provider_instance_id"]
    except Exception as e:
        raise HTTPException(status_code=502, detail={
            "error": "PROVIDER_ERROR",
            "message": f"Provider failed to create instance: {str(e)}",
        })
    instance = await create_instance(
        user_id=request.state.user_id,
        provider=offering["provider"],
        gpu_offering_id=body.gpu_offering_id,
        config_json=json.dumps(config),
        agent_token=agent_token,
        provider_instance_id=provider_instance_id,
    )
    await log_budget(request.state.user_id, instance["id"], "create", estimated_total)
    start_lifecycle_advance(instance["id"])
    return {
        "instance": instance,
        "estimated_cost": estimated_total,
    }


@router.get("")
async def list_instances(request: Request, _payload: dict = Depends(require_auth)):
    instances = await get_user_instances(request.state.user_id)
    return {"instances": instances}


@router.get("/{instance_id}")
async def detail(request: Request, instance_id: str, _payload: dict = Depends(require_auth)):
    instance = await get_instance(instance_id)
    if instance is None or instance["user_id"] != request.state.user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Instance not found"})
    metrics = await get_latest_metrics(instance_id)
    return {"instance": instance, "metrics": metrics}


@router.delete("/{instance_id}")
async def delete(request: Request, instance_id: str, _payload: dict = Depends(require_auth)):
    instance = await get_instance(instance_id)
    if instance is None or instance["user_id"] != request.state.user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Instance not found"})
    provider = MockProvider()
    await provider.destroy_instance(instance["provider_instance_id"])
    await destroy_instance(instance_id)
    return {"status": "destroyed"}


@router.get("/{instance_id}/metrics")
async def metrics(request: Request, instance_id: str, _payload: dict = Depends(require_auth)):
    instance = await get_instance(instance_id)
    if instance is None or instance["user_id"] != request.state.user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Instance not found"})
    latest = await get_latest_metrics(instance_id)
    history = await get_metrics_history(instance_id)
    return {"latest": latest, "history": history}


class EstimateRequest(BaseModel):
    gpu_offering_id: str
    duration_h: int = 1


@router.post("/estimate")
async def estimate(request: Request, body: EstimateRequest, _payload: dict = Depends(require_auth)):
    offering = await get_gpu_offering(body.gpu_offering_id)
    if offering is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "GPU offering not found"})
    estimated_total = offering["price_per_hour"] * body.duration_h
    remaining = await get_remaining_budget(request.state.user_id)
    return {
        "price_per_hour": offering["price_per_hour"],
        "estimated_total": estimated_total,
        "remaining_budget": round(remaining, 2),
    }


class BindInstanceRequest(BaseModel):
    provider_instance_id: str
    provider: str
    gpu_offering_id: str
    template: str = "nvidia/pytorch:26.03-py3"
    disk_gb: int = 200
    duration_h: int = 1


@router.post("/bind")
async def bind_instance(request: Request, body: BindInstanceRequest, _payload: dict = Depends(require_auth)):
    """Bind an existing GPU instance created externally (naguan mode)."""
    offering = await get_gpu_offering(body.gpu_offering_id)
    if offering is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "GPU offering not found"})
    config = {
        "template": body.template,
        "disk_gb": body.disk_gb,
        "duration_h": body.duration_h,
        "bind_mode": True,
    }
    agent_token = secrets.token_hex(16)
    instance = await create_instance(
        user_id=request.state.user_id,
        provider=body.provider,
        gpu_offering_id=body.gpu_offering_id,
        config_json=json.dumps(config),
        agent_token=agent_token,
        provider_instance_id=body.provider_instance_id,
    )
    await update_instance_status(instance["id"], status="ready", current_step=6, progress_percent=100.0)
    return {"instance": instance, "agent_token": agent_token}
