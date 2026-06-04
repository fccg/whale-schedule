import pytest
from app.services.instance_service import check_degraded_instances
from app.models.instance import update_heartbeat, update_instance_status


async def _create_test_instance(auth_client):
    """Helper: create an instance using a known mock offering."""
    from app.models.gpu_offering import seed_mock_offerings
    await seed_mock_offerings()
    resp = await auth_client.post("/api/instances", json={
        "gpu_offering_id": "mock-a100-1", "duration_h": 1,
    })
    assert resp.status_code == 200, f"Create failed: {resp.text}"
    data = resp.json()
    return data["instance"]["id"], data["instance"]["agent_token"]


@pytest.mark.asyncio
async def test_degraded_detection_after_timeout(auth_client, raw_client):
    """Instance with stale heartbeat should be marked degraded."""
    instance_id, agent_token = await _create_test_instance(auth_client)

    # Heartbeat once to set last_heartbeat_at
    await raw_client.post("/api/agent/heartbeat", json={
        "agent_token": agent_token,
        "instance_id": instance_id,
    })

    # Advance to ready
    await update_instance_status(instance_id, status="ready", current_step=6, progress_percent=100.0)

    # Manually set heartbeat to old timestamp
    from app.database import get_db
    db = await get_db()
    await db.execute(
        "UPDATE instances SET last_heartbeat_at = datetime('now', '-60 seconds') WHERE id = ?",
        (instance_id,),
    )
    await db.commit()

    await check_degraded_instances()

    from app.models.instance import get_instance
    inst = await get_instance(instance_id)
    assert inst is not None
    assert inst["status"] == "degraded"
    assert "Heartbeat timeout" in (inst["last_error"] or "")


@pytest.mark.asyncio
async def test_heartbeat_recovery_from_degraded(auth_client, raw_client):
    """Heartbeat should recover instance from degraded to ready."""
    instance_id, agent_token = await _create_test_instance(auth_client)

    await update_instance_status(instance_id, status="degraded", last_error="Heartbeat timeout")

    # Send heartbeat to recover
    resp = await raw_client.post("/api/agent/heartbeat", json={
        "agent_token": agent_token,
        "instance_id": instance_id,
        "cpu_percent": 50.0,
    })
    assert resp.status_code == 200

    from app.models.instance import get_instance
    inst = await get_instance(instance_id)
    assert inst["status"] == "ready"
    assert inst["last_error"] is None


@pytest.mark.asyncio
async def test_provisioning_to_ready_via_heartbeat(auth_client, raw_client):
    """Bootstrap done heartbeat should advance provisioning -> testing -> ready."""
    instance_id, agent_token = await _create_test_instance(auth_client)

    # Bootstrap done heartbeat
    resp = await raw_client.post("/api/agent/heartbeat", json={
        "agent_token": agent_token,
        "instance_id": instance_id,
        "bootstrap_step": 6,
        "bootstrap_total": 6,
        "bootstrap_status": "done",
    })
    assert resp.status_code == 200

    from app.models.instance import get_instance
    inst = await get_instance(instance_id)
    assert inst is not None
    assert inst["status"] in ("testing", "ready")


@pytest.mark.asyncio
async def test_bootstrap_failure(auth_client, raw_client):
    """Bootstrap failure should set instance to failed."""
    instance_id, agent_token = await _create_test_instance(auth_client)

    resp = await raw_client.post("/api/agent/heartbeat", json={
        "agent_token": agent_token,
        "instance_id": instance_id,
        "bootstrap_step": 3,
        "bootstrap_total": 6,
        "bootstrap_status": "failed",
        "last_error": "CUDA install failed",
    })
    assert resp.status_code == 200

    from app.models.instance import get_instance
    inst = await get_instance(instance_id)
    assert inst["status"] == "failed"
    assert "CUDA" in (inst["last_error"] or "")


@pytest.mark.asyncio
async def test_last_error_can_be_cleared(auth_client, raw_client):
    """last_error should be cleareable."""
    instance_id, agent_token = await _create_test_instance(auth_client)

    # Set error
    await update_instance_status(instance_id, status="bootstrapping", last_error="Some error")

    # Bootstrap done should clear error
    resp = await raw_client.post("/api/agent/heartbeat", json={
        "agent_token": agent_token,
        "instance_id": instance_id,
        "bootstrap_step": 6,
        "bootstrap_total": 6,
        "bootstrap_status": "done",
    })
    assert resp.status_code == 200

    from app.models.instance import get_instance
    inst = await get_instance(instance_id)
    assert inst["last_error"] is None
