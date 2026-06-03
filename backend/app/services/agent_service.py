import json
from app.models.instance import update_heartbeat
from app.models.metric import insert_metric


async def handle_heartbeat(instance_id: str, payload: dict):
    await update_heartbeat(instance_id)

    # Recover from degraded if heartbeat resumed
    from app.models.instance import get_instance as _get_instance, update_instance_status as _update_status
    inst = await _get_instance(instance_id)
    if inst and inst["status"] == "degraded":
        await _update_status(instance_id, status="ready", last_error=None)

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
