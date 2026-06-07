import json
import logging
import secrets
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from app.middleware.auth import require_auth
from app.models.instance import create_instance, get_instance, get_user_instances, destroy_instance, update_instance_status
from app.models.metric import get_latest_metrics, get_metrics_history
from app.services.instance_service import start_lifecycle_advance
from app.services.budget_service import log_provider_budget
from app.services.provider_registry import get_provider, is_provider_enabled
from app.services.market_service import build_funding_summary, get_market_offering
from app.services.dashboard_service import build_instance_dashboard

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/instances", tags=["instances"])


def _resolve_limiting_factor(wallet_balance: float, provider_budget_remaining: float | None) -> str:
    if provider_budget_remaining is None:
        return "none"
    return "wallet" if wallet_balance <= provider_budget_remaining else "provider_budget"


class CreateInstanceRequest(BaseModel):
    gpu_offering_id: str
    template: str = "nvidia/pytorch:26.03-py3"
    disk_gb: int = 200
    duration_h: int = 1


@router.post("")
async def create(request: Request, body: CreateInstanceRequest, _payload: dict = Depends(require_auth)):
    offering = await get_market_offering(body.gpu_offering_id)
    if offering is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "GPU offering not found"})

    provider_name = offering["provider"]
    if not is_provider_enabled(provider_name):
        raise HTTPException(status_code=400, detail={
            "error": "PROVIDER_DISABLED",
            "message": f"Provider {provider_name} is not enabled",
        })

    logger.info("Instance create started: user=%s provider=%s offering=%s",
                request.state.user_id, provider_name, body.gpu_offering_id)

    estimated_total = offering["price_per_hour"] * body.duration_h
    funding = await build_funding_summary(offering, body.duration_h)
    if funding["wallet_balance"] < estimated_total:
        raise HTTPException(status_code=422, detail={
            "error": "PROVIDER_WALLET_INSUFFICIENT",
            "message": "AutoDL wallet balance is insufficient",
        })
    provider_budget_remaining = funding.get("provider_budget_remaining")
    if funding["provider_budget_enabled"] and provider_budget_remaining is not None and provider_budget_remaining < estimated_total:
        raise HTTPException(status_code=422, detail={
            "error": "PROVIDER_BUDGET_EXCEEDED",
            "message": "Estimated cost exceeds platform AutoDL budget",
        })

    metadata = offering.get("metadata", {})
    if not metadata and offering.get("metadata_json"):
        try:
            metadata = json.loads(offering["metadata_json"])
        except (json.JSONDecodeError, TypeError):
            metadata = {}
    config = {
        "template": body.template,
        "disk_gb": body.disk_gb,
        "duration_h": body.duration_h,
        "gpu_spec_uuid": metadata.get("gpu_spec_uuid", ""),
        "image_uuid": metadata.get("image_uuid", ""),
        "cuda_v_from": metadata.get("cuda_v_from", 113),
        "gpu_amount": metadata.get("gpu_amount", 1),
        "instance_name": f"schedule-{body.gpu_offering_id[:12]}",
        "start_command": "sleep 1",
    }
    agent_token = secrets.token_hex(16)
    provider = get_provider(provider_name)
    logger.info("Autodl create config: gpu_spec_uuid=%s, image_uuid=%s, cuda_v_from=%s, gpu_amount=%s",
                config["gpu_spec_uuid"], config["image_uuid"], config["cuda_v_from"], config["gpu_amount"])

    try:
        provider_result = await provider.create_instance(body.gpu_offering_id, config)
        provider_instance_id = provider_result["provider_instance_id"]
    except Exception as e:
        logger.warning("Instance create provider failed: user=%s provider=%s error=%s",
                       request.state.user_id, provider_name, e)
        raise HTTPException(status_code=502, detail={
            "error": "PROVIDER_ERROR",
            "message": f"Provider failed to create instance: {str(e)}",
        })

    instance = await create_instance(
        user_id=request.state.user_id,
        provider=provider_name,
        gpu_offering_id=body.gpu_offering_id,
        config_json=json.dumps(config),
        agent_token=agent_token,
        provider_instance_id=provider_instance_id,
        ssh_host=provider_result.get("ssh_host"),
        ssh_port=provider_result.get("ssh_port"),
        connect_url=provider_result.get("connect_url"),
        jupyter_url=provider_result.get("jupyter_url"),
        hourly_price=provider_result.get("hourly_price") or offering["price_per_hour"],
        region=provider_result.get("region") or offering.get("region"),
    )

    if funding["provider_budget_enabled"]:
        await log_provider_budget(request.state.user_id, instance["id"], provider_name, "create", estimated_total)
    logger.info("Instance created: id=%s user=%s provider=%s",
                instance["id"], request.state.user_id, provider_name)
    start_lifecycle_advance(instance["id"])

    try:
        snapshot = await provider.get_instance(provider_instance_id)
        await update_instance_status(
            instance["id"], status=instance["status"],
            ssh_host=snapshot.get("ssh_host"),
            ssh_port=snapshot.get("ssh_port"),
            connect_url=snapshot.get("connect_url"),
            jupyter_url=snapshot.get("jupyter_url"),
            hourly_price=snapshot.get("hourly_price"),
            region=snapshot.get("region"),
        )
    except Exception:
        logger.warning("Failed to enrich instance with snapshot info", exc_info=True)

    provider_budget_remaining_after = None
    if funding["provider_budget_enabled"] and provider_budget_remaining is not None:
        provider_budget_remaining_after = max(0.0, provider_budget_remaining - estimated_total)
    effective_available = funding["wallet_balance"] if provider_budget_remaining_after is None else min(
        funding["wallet_balance"], provider_budget_remaining_after
    )

    return {
        "instance": await get_instance(instance["id"]),
        "estimated_cost": estimated_total,
        "funding": {
            "provider": provider_name,
            "estimated_total": estimated_total,
            "wallet_balance": funding["wallet_balance"],
            "wallet_currency": funding["wallet_currency"],
            "provider_budget_enabled": funding["provider_budget_enabled"],
            "provider_budget_total": funding["provider_budget_total"],
            "provider_budget_remaining": round(provider_budget_remaining_after, 2) if provider_budget_remaining_after is not None else None,
            "effective_available": round(effective_available, 2),
            "limiting_factor": _resolve_limiting_factor(funding["wallet_balance"], provider_budget_remaining_after),
        },
    }


@router.get("")
async def list_instances(request: Request, _payload: dict = Depends(require_auth)):
    instances = await get_user_instances(request.state.user_id)
    enriched = []
    for instance in instances:
        offering = await get_market_offering(instance["gpu_offering_id"]) if instance.get("gpu_offering_id") else None
        enriched.append({
            **instance,
            "offering": offering,
        })
    return {"instances": enriched}


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
    if not is_provider_enabled(instance["provider"]):
        raise HTTPException(status_code=400, detail={
            "error": "PROVIDER_DISABLED",
            "message": f"Provider {instance['provider']} is not enabled",
        })
    logger.info("Instance destroy started: id=%s provider=%s user=%s",
                instance_id, instance["provider"], request.state.user_id)
    provider = get_provider(instance["provider"])
    try:
        await provider.destroy_instance(instance["provider_instance_id"])
    except Exception as e:
        logger.warning(f"Provider destroy failed for {instance_id}: {e}", exc_info=True)
    await destroy_instance(instance_id)
    logger.info("Instance destroyed: id=%s", instance_id)
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
async def estimate(body: EstimateRequest, _payload: dict = Depends(require_auth)):
    offering = await get_market_offering(body.gpu_offering_id)
    if offering is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "GPU offering not found"})
    funding = await build_funding_summary(offering, body.duration_h)
    return {
        "price_per_hour": offering["price_per_hour"],
        "estimated_total": funding["estimated_total"],
        "remaining_budget": funding["effective_available"],
        "funding": funding,
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
    offering = await get_market_offering(body.gpu_offering_id)
    if offering is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "GPU offering not found"})
    if offering["provider"] != body.provider:
        raise HTTPException(status_code=400, detail={
            "error": "PROVIDER_MISMATCH",
            "message": f"Offering provider {offering['provider']} does not match bind provider {body.provider}",
        })
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


@router.get("/{instance_id}/dashboard")
async def dashboard(request: Request, instance_id: str, _payload: dict = Depends(require_auth)):
    instance = await get_instance(instance_id)
    if instance is None or instance["user_id"] != request.state.user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Instance not found"})
    payload = await build_instance_dashboard(instance)
    return payload
