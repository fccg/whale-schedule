import json
import pytest
from app.services.dashboard_service import build_instance_dashboard, _build_connect, _build_runtime


@pytest.mark.asyncio
async def test_dashboard_without_metrics(auth_client, raw_client):
    """Dashboard should return valid structure even without metrics."""
    from app.models.gpu_offering import seed_mock_offerings
    await seed_mock_offerings()

    resp = await auth_client.post("/api/instances", json={
        "gpu_offering_id": "mock-a100-1",
        "duration_h": 1,
    })
    assert resp.status_code == 200, f"Create failed: {resp.text}"
    instance_id = resp.json()["instance"]["id"]

    resp = await auth_client.get(f"/api/instances/{instance_id}/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "instance" in data
    assert "runtime" in data
    assert "latest_metric" in data
    assert "connect" in data
    assert "connectivity_summary" in data
    assert "tests_summary" in data
    assert "metric_history" in data


@pytest.mark.asyncio
async def test_dashboard_with_metrics(auth_client, raw_client):
    """Dashboard with heartbeat data should have real metrics."""
    from app.models.gpu_offering import seed_mock_offerings
    await seed_mock_offerings()

    resp = await auth_client.post("/api/instances", json={
        "gpu_offering_id": "mock-a100-1",
        "duration_h": 1,
    })
    assert resp.status_code == 200, f"Create failed: {resp.text}"
    instance = resp.json()["instance"]
    instance_id = instance["id"]
    agent_token = instance["agent_token"]

    await raw_client.post("/api/agent/heartbeat", json={
        "agent_token": agent_token,
        "instance_id": instance_id,
        "cpu_percent": 45.0,
        "memory_percent": 30.0,
        "memory_used_gb": 14.0,
        "memory_total_gb": 46.6,
        "disk_used_gb": 25.0,
        "disk_total_gb": 200.0,
        "net_up_mbps": 100.0,
        "net_down_mbps": 400.0,
        "gpus": [{"index": 0, "utilization": 80, "vram_percent": 60, "vram_used_gb": 27.0, "vram_total_gb": 45.0, "temp_c": 55.0, "power_w": 200.0}],
    })

    resp = await auth_client.get(f"/api/instances/{instance_id}/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["latest_metric"] is not None
    assert data["latest_metric"]["cpu_percent"] == 45.0


@pytest.mark.asyncio
async def test_dashboard_empty_instance(auth_client):
    """Dashboard with no data should still return valid structure."""
    mock_instance = {
        "id": "test-nonexistent",
        "user_id": "test",
        "provider": "mock",
        "provider_instance_id": None,
        "gpu_offering_id": None,
        "status": "provisioning",
        "current_step": 0,
        "progress_percent": 0,
        "last_error": None,
        "agent_token": None,
        "last_heartbeat_at": None,
        "display_name": None,
        "hourly_price": None,
        "region": None,
        "ssh_host": None,
        "ssh_port": None,
        "connect_url": None,
        "jupyter_url": None,
        "metadata_json": "{}",
        "config_json": "{}",
        "created_at": "2026-01-01T00:00:00",
        "destroyed_at": None,
    }
    data = await build_instance_dashboard(mock_instance)
    assert "instance" in data
    assert "runtime" in data
    assert "connect" in data
    assert "offering" in data or data["offering"] is None


def test_build_connect_uses_real_fields():
    instance_with_real = {
        "id": "test-id-12345678",
        "ssh_host": "real-host.example.com",
        "ssh_port": 22022,
        "jupyter_url": "https://real-jupyter.example.com/lab",
        "connect_url": "ssh://real-host.example.com:22022",
    }
    connect = _build_connect(instance_with_real)
    assert connect["ssh_host"] == "real-host.example.com"
    assert connect["ssh_port"] == 22022
    assert connect["jupyter_url"] == "https://real-jupyter.example.com/lab"


def test_build_connect_falls_back_to_mock():
    instance_mock = {
        "id": "test-id-12345678",
        "ssh_host": None,
        "ssh_port": None,
        "jupyter_url": None,
    }
    connect = _build_connect(instance_mock)
    assert connect["ssh_host"] is not None
    assert "mock-" in connect["ssh_host"]


def test_build_runtime_computes_uptime():
    from datetime import datetime, timezone, timedelta
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    instance = {
        "id": "test",
        "created_at": past,
        "status": "ready",
    }
    runtime = _build_runtime(instance, None, None)
    assert runtime["uptime_seconds"] >= 3000
    assert runtime["gpus"] == []
