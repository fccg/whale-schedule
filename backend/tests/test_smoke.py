import pytest


@pytest.mark.asyncio
async def test_smoke_full_lifecycle(auth_client, raw_client):
    from app.models.gpu_offering import seed_mock_offerings
    await seed_mock_offerings()

    resp = await auth_client.get("/api/gpus")
    assert resp.status_code == 200
    gpus = resp.json()["gpus"]
    assert len(gpus) >= 1
    gpu_id = gpus[0]["id"]

    resp = await auth_client.post("/api/instances/estimate", json={"gpu_offering_id": gpu_id, "duration_h": 1})
    assert resp.status_code == 200
    est = resp.json()
    assert "remaining_budget" in est

    resp = await auth_client.post("/api/instances", json={"gpu_offering_id": gpu_id, "duration_h": 1})
    assert resp.status_code == 200
    instance = resp.json()["instance"]
    instance_id = instance["id"]
    agent_token = instance["agent_token"]

    import asyncio
    await asyncio.sleep(1)

    resp = await auth_client.get(f"/api/instances/{instance_id}")
    assert resp.status_code == 200

    resp = await auth_client.get("/api/instances")
    assert resp.status_code == 200
    assert len(resp.json()["instances"]) >= 1

    resp = await raw_client.post("/api/agent/heartbeat", json={
        "agent_token": agent_token,
        "instance_id": instance_id,
        "cpu_percent": 45.0,
        "gpus": [{"index": 0, "utilization": 80, "vram_percent": 60}],
    })
    assert resp.status_code == 200

    resp = await auth_client.get("/api/budget")
    assert resp.status_code == 200

    resp = await auth_client.delete(f"/api/instances/{instance_id}")
    assert resp.status_code == 200
