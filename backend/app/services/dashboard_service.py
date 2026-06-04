import json
import logging
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models.gpu_offering import get_gpu_offering
from app.models.metric import get_latest_metrics, get_metrics_history

logger = logging.getLogger(__name__)


def _parse_gpus(latest_metric: dict | None) -> list[dict]:
    if not latest_metric:
        return []
    gpu_json = latest_metric.get("gpu_json")
    if gpu_json:
        try:
            return json.loads(gpu_json)
        except json.JSONDecodeError:
            return []
    return []


def _build_runtime(instance: dict, latest_metric: dict | None, offering: dict | None) -> dict:
    gpus = _parse_gpus(latest_metric)
    if not gpus and offering:
        gpus = [{
            "index": 0,
            "utilization": None,
            "vram_percent": None,
            "vram_used_gb": None,
            "vram_total_gb": offering.get("vram_gb", 0),
            "temp_c": None,
            "power_w": None,
        }]

    created_at = instance.get("created_at")
    uptime_seconds = 0
    if created_at:
        try:
            created_str = created_at.replace("Z", "+00:00")
            created_dt = datetime.fromisoformat(created_str)
            if created_dt.tzinfo is None:
                from datetime import timezone as tz
                created_dt = created_dt.replace(tzinfo=tz.utc)
            now = datetime.now(timezone.utc)
            uptime_seconds = max(0, int((now - created_dt).total_seconds()))
        except Exception:
            uptime_seconds = 0

    return {
        "uptime_seconds": int(uptime_seconds),
        "process_count": None,
        "disk_used_gb": latest_metric.get("disk_used_gb") if latest_metric else None,
        "disk_total_gb": latest_metric.get("disk_total_gb") if latest_metric else (offering.get("disk_gb") if offering else None),
        "volume_used_gb": None,
        "volume_total_gb": None,
        "driver_version": None,
        "cuda_version": None,
        "pstate": None,
        "gpus": gpus,
    }


def _build_connect(instance: dict) -> dict:
    return {
        "jupyter_url": instance.get("jupyter_url") or _mock_jupyter(instance),
        "ssh_host": instance.get("ssh_host") or _mock_ssh_host(instance),
        "ssh_port": instance.get("ssh_port") or 40275,
        "docker_image": "nvidia/pytorch:26.03-py3",
        "image_runtype": "jupyter_direct ssh",
        "env": {"JUPYTER_DIR": "/workspace"},
        "command_preview": "echo starting up",
    }


def _mock_jupyter(instance: dict) -> str | None:
    short_id = instance.get("id", "unknown")[:8]
    return f"https://mock-{short_id}.gpu-schedule.local/lab"


def _mock_ssh_host(instance: dict) -> str | None:
    short_id = instance.get("id", "unknown")[:8]
    return f"mock-{short_id}.gpu-schedule.local"


def _mock_latest_metric(instance: dict, offering: dict | None) -> dict:
    vram_total = offering["vram_gb"] if offering else 48.0
    gpus = [{
        "index": 0,
        "utilization": None,
        "vram_percent": None,
        "vram_used_gb": None,
        "vram_total_gb": vram_total,
        "temp_c": None,
        "power_w": None,
    }]
    return {
        "id": 0,
        "instance_id": instance["id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu_percent": None,
        "memory_percent": None,
        "memory_used_gb": None,
        "memory_total_gb": None,
        "gpu_util_percent": None,
        "gpu_vram_percent": None,
        "disk_used_gb": None,
        "disk_total_gb": None,
        "net_up_mbps": None,
        "net_down_mbps": None,
        "gpu_json": json.dumps(gpus),
    }


def _mock_history(instance: dict) -> list[dict]:
    return []


async def _get_connectivity_summary(instance_id: str) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM connectivity_tests WHERE instance_id = ? ORDER BY timestamp DESC LIMIT 5",
        (instance_id,),
    )
    return [dict(row) for row in await cursor.fetchall()]


async def _get_tests_summary(instance_id: str) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM test_runs WHERE instance_id = ? ORDER BY started_at DESC LIMIT 5",
        (instance_id,),
    )
    runs = [dict(row) for row in await cursor.fetchall()]
    for run in runs:
        cursor2 = await db.execute(
            "SELECT * FROM test_results WHERE test_run_id = ? ORDER BY id",
            (run["id"],),
        )
        run["results"] = [dict(row) for row in await cursor2.fetchall()]
    return runs


async def build_instance_dashboard(instance: dict) -> dict:
    offering = await get_gpu_offering(instance.get("gpu_offering_id")) if instance.get("gpu_offering_id") else None
    latest_metric = await get_latest_metrics(instance["id"])
    history = await get_metrics_history(instance["id"])

    has_real_data = latest_metric is not None
    if not has_real_data:
        latest_metric = _mock_latest_metric(instance, offering)
    if not history:
        history = _mock_history(instance)

    runtime = _build_runtime(instance, latest_metric, offering)

    return {
        "instance": instance,
        "offering": offering,
        "runtime": runtime,
        "latest_metric": latest_metric,
        "metric_history": history,
        "connect": _build_connect(instance),
        "connectivity_summary": await _get_connectivity_summary(instance["id"]),
        "tests_summary": await _get_tests_summary(instance["id"]),
    }
