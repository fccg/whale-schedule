import pytest


@pytest.mark.asyncio
async def test_smoke_full_lifecycle(auth_client, raw_client):
    from app.models.gpu_offering import seed_mock_offerings
    await seed_mock_offerings()

    resp = await auth_client.get("/api/gpus")
    assert resp.status_code == 200
    gpus = resp.json()["gpus"]
    assert len(gpus) >= 1
    gpu_id = "mock-a100-1"

    resp = await auth_client.get(f"/api/gpus/{gpu_id}/launch")
    assert resp.status_code == 200
    launch = resp.json()
    assert launch["funding"]["provider"] == "mock"
    assert launch["funding"]["wallet_balance"] == 9999.0
    assert launch["funding"]["provider_budget_enabled"] is False

    resp = await auth_client.post("/api/instances/estimate", json={"gpu_offering_id": gpu_id, "duration_h": 1})
    assert resp.status_code == 200
    est = resp.json()
    assert "remaining_budget" in est
    assert est["remaining_budget"] == est["funding"]["effective_available"]

    resp = await auth_client.post("/api/instances", json={"gpu_offering_id": gpu_id, "duration_h": 1})
    assert resp.status_code == 200
    create_payload = resp.json()
    assert create_payload["funding"]["wallet_balance"] == 9999.0
    instance = create_payload["instance"]
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
