import json
import pytest
from app.services.test_service import export_test_results


async def _create_test_instance(auth_client):
    """Helper: create an instance using a known mock offering."""
    from app.models.gpu_offering import seed_mock_offerings
    await seed_mock_offerings()
    resp = await auth_client.post("/api/instances", json={
        "gpu_offering_id": "mock-a100-1", "duration_h": 1,
    })
    assert resp.status_code == 200, f"Create failed: {resp.text}"
    return resp.json()["instance"]["id"]


@pytest.mark.asyncio
async def test_export_json_empty(auth_client, raw_client):
    """Export empty results should return valid JSON."""
    instance_id = await _create_test_instance(auth_client)

    resp = await auth_client.get(f"/api/instances/{instance_id}/tests/export?format=json")
    assert resp.status_code == 200
    data = resp.json()
    if "results" not in data:
        data = json.loads(resp.text) if isinstance(resp.text, str) else data
    assert "results" in data


@pytest.mark.asyncio
async def test_export_csv(auth_client, raw_client):
    """Export CSV should return text/csv content type."""
    instance_id = await _create_test_instance(auth_client)

    resp = await auth_client.get(f"/api/instances/{instance_id}/tests/export?format=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_export_json_with_data(auth_client, raw_client):
    """Export after running perf test should return results."""
    from app.models.instance import update_instance_status
    instance_id = await _create_test_instance(auth_client)
    await update_instance_status(instance_id, status="ready", current_step=6, progress_percent=100.0)

    resp = await auth_client.post(f"/api/instances/{instance_id}/tests", json={"type": "perf"})
    assert resp.status_code == 200

    resp = await auth_client.get(f"/api/instances/{instance_id}/tests/export?format=json")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) > 0


@pytest.mark.asyncio
async def test_export_invalid_format(auth_client):
    """Invalid format should return 400."""
    instance_id = await _create_test_instance(auth_client)

    resp = await auth_client.get(f"/api/instances/{instance_id}/tests/export?format=xml")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_connectivity_test_triggers(auth_client, raw_client):
    """Connectivity test should store data and be retrievable."""
    from app.models.instance import update_instance_status
    instance_id = await _create_test_instance(auth_client)
    await update_instance_status(instance_id, status="ready", current_step=6, progress_percent=100.0)

    resp = await auth_client.post(f"/api/instances/{instance_id}/connectivity")
    assert resp.status_code == 200

    resp = await auth_client.get(f"/api/instances/{instance_id}/connectivity")
    assert resp.status_code == 200
    data = resp.json()
    assert "connectivity_tests" in data
    assert len(data["connectivity_tests"]) >= 5
