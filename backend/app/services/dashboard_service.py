import json
from datetime import datetime, timedelta
from app.database import get_db
from app.models.gpu_offering import get_gpu_offering
from app.models.metric import get_latest_metrics, get_metrics_history


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
            "utilization": 89 if instance["status"] == "ready" else 42,
            "vram_percent": 93 if instance["status"] == "ready" else 38,
            "vram_used_gb": round(offering["vram_gb"] * 0.93, 1) if instance["status"] == "ready" else round(offering["vram_gb"] * 0.38, 1),
            "vram_total_gb": offering["vram_gb"],
            "temp_c": 61.0,
            "power_w": 244.0,
        }]
    return {
        "uptime_seconds": 4020 if instance["status"] == "ready" else 780,
        "process_count": 345 if instance["status"] == "ready" else 84,
        "disk_used_gb": latest_metric.get("disk_used_gb") if latest_metric else 25.0,
        "disk_total_gb": latest_metric.get("disk_total_gb") if latest_metric else (offering["disk_gb"] if offering else 200.0),
        "volume_used_gb": None,
        "volume_total_gb": None,
        "driver_version": "565.57.01",
        "cuda_version": "12.7",
        "pstate": "P0" if instance["status"] == "ready" else "P2",
        "gpus": gpus,
    }


def _mock_latest_metric(instance: dict, offering: dict | None) -> dict:
    vram_total = offering["vram_gb"] if offering else 48.0
    gpus = [{
        "index": 0,
        "utilization": 89 if instance["status"] == "ready" else 52,
        "vram_percent": 93 if instance["status"] == "ready" else 44,
        "vram_used_gb": round(vram_total * 0.93, 1) if instance["status"] == "ready" else round(vram_total * 0.44, 1),
        "vram_total_gb": vram_total,
        "temp_c": 61.0,
        "power_w": 244.0,
    }]
    return {
        "id": 0,
        "instance_id": instance["id"],
        "timestamp": datetime.utcnow().isoformat(),
        "cpu_percent": 100 if instance["status"] == "ready" else 48,
        "memory_percent": 16 if instance["status"] == "ready" else 28,
        "memory_used_gb": 7.8,
        "memory_total_gb": 46.6,
        "gpu_util_percent": gpus[0]["utilization"],
        "gpu_vram_percent": gpus[0]["vram_percent"],
        "disk_used_gb": 25.0,
        "disk_total_gb": 200.0,
        "net_up_mbps": 125.3,
        "net_down_mbps": 450.1,
        "gpu_json": json.dumps(gpus),
    }


def _mock_history(instance: dict) -> list[dict]:
    base = datetime.utcnow()
    cpu_values = [12, 18, 24, 35, 48, 56, 72, 86, 100]
    gpu_values = [8, 16, 24, 32, 44, 57, 70, 82, 89]
    mem_values = [8, 9, 10, 12, 13, 14, 15, 16, 16]
    history = []
    for index, cpu in enumerate(cpu_values):
        history.append({
            "id": index + 1,
            "instance_id": instance["id"],
            "timestamp": (base - timedelta(minutes=(len(cpu_values) - index) * 3)).isoformat(),
            "cpu_percent": cpu,
            "memory_percent": mem_values[index],
            "memory_used_gb": 7.8,
            "memory_total_gb": 46.6,
            "gpu_util_percent": gpu_values[index],
            "gpu_vram_percent": min(96, gpu_values[index] + 8),
            "disk_used_gb": 25.0,
            "disk_total_gb": 200.0,
            "net_up_mbps": 125.3,
            "net_down_mbps": 450.1,
            "gpu_json": None,
        })
    return history


def _build_connect(instance: dict) -> dict:
    short_id = instance["id"][:8]
    return {
        "jupyter_url": f"https://mock-{short_id}.gpu-schedule.local/lab",
        "ssh_host": f"mock-{short_id}.gpu-schedule.local",
        "ssh_port": 40275,
        "docker_image": "pytorch/pytorch",
        "image_runtype": "jupyter_direct ssh",
        "env": {"JUPYTER_DIR": "/workspace"},
        "command_preview": "echo starting up",
    }


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
    offering = await get_gpu_offering(instance["gpu_offering_id"]) if instance.get("gpu_offering_id") else None
    latest_metric = await get_latest_metrics(instance["id"])
    history = await get_metrics_history(instance["id"])
    if latest_metric is None:
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
