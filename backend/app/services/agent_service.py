import json
import logging
from app.models.instance import update_heartbeat, update_instance_status
from app.models.metric import insert_metric

logger = logging.getLogger(__name__)


async def handle_heartbeat(instance_id: str, payload: dict):
    await update_heartbeat(instance_id)

    from app.models.instance import get_instance as _get_instance
    inst = await _get_instance(instance_id)
    if not inst:
        return

    current_status = inst.get("status", "provisioning")

    # Process bootstrap progress if reported
    bootstrap_step = payload.get("bootstrap_step")
    bootstrap_total = payload.get("bootstrap_total", 6)
    bootstrap_status = payload.get("bootstrap_status")

    if bootstrap_step is not None and bootstrap_status is not None:
        if bootstrap_status == "failed":
            await update_instance_status(
                instance_id,
                status="failed",
                current_step=bootstrap_step,
                progress_percent=round(bootstrap_step / bootstrap_total * 100, 1),
                last_error=payload.get("last_error", f"Bootstrap step {bootstrap_step} failed"),
            )
            return
        elif bootstrap_status == "running":
            if current_status not in ("ready", "degraded", "failed", "destroyed"):
                new_status = "bootstrapping" if bootstrap_step <= 4 else "testing"
                await update_instance_status(
                    instance_id,
                    status=new_status,
                    current_step=bootstrap_step,
                    progress_percent=round(bootstrap_step / bootstrap_total * 100, 1),
                )
        elif bootstrap_status == "done":
            if current_status not in ("ready", "degraded", "failed", "destroyed"):
                await update_instance_status(
                    instance_id,
                    status="testing",
                    current_step=bootstrap_step,
                    progress_percent=100.0,
                )
                # Bootstrap complete, auto-advance to ready on first metrics heartbeat
                await update_instance_status(
                    instance_id,
                    status="ready",
                    current_step=bootstrap_step,
                    progress_percent=100.0,
                    clear_error=True,
                )

    # Recover from degraded if heartbeat resumed
    if current_status == "degraded":
        await update_instance_status(instance_id, status="ready", clear_error=True)
    elif current_status == "failed" and payload.get("bootstrap_status") == "running":
        # Allow recovery from failed if bootstrap restarts
        await update_instance_status(instance_id, status="bootstrapping", clear_error=True)

    # Store last_error from agent if provided
    last_error = payload.get("last_error")
    if last_error and current_status not in ("failed",):
        await update_instance_status(instance_id, status=current_status, last_error=last_error)

    # Process metrics
    gpu_json = None
    if "gpus" in payload:
        gpu_json = json.dumps(payload["gpus"])

    gpus = payload.get("gpus")
    gpu_util_percent = None
    gpu_vram_percent = None
    if gpus and isinstance(gpus, list) and len(gpus) > 0:
        gpu_util_percent = gpus[0].get("utilization")
        gpu_vram_percent = gpus[0].get("vram_percent")

    await insert_metric(
        instance_id=instance_id,
        cpu_percent=payload.get("cpu_percent"),
        memory_percent=payload.get("memory_percent"),
        memory_used_gb=payload.get("memory_used_gb"),
        memory_total_gb=payload.get("memory_total_gb"),
        gpu_util_percent=gpu_util_percent,
        gpu_vram_percent=gpu_vram_percent,
        disk_used_gb=payload.get("disk_used_gb"),
        disk_total_gb=payload.get("disk_total_gb"),
        net_up_mbps=payload.get("net_up_mbps"),
        net_down_mbps=payload.get("net_down_mbps"),
        gpu_json=gpu_json,
    )
