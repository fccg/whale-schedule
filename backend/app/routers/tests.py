import uuid
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from pydantic import BaseModel
from app.middleware.auth import require_auth
from app.models.instance import get_instance
from app.database import get_db

router = APIRouter(prefix="/api/instances", tags=["tests"])


class TriggerTestRequest(BaseModel):
    type: str  # "perf" or "connectivity"


def _generate_mock_results(test_run_id: str, test_type: str) -> list[dict]:
    if test_type == "perf":
        return [
            {"metric_name": "GPU Memory Bandwidth", "value": 1550.0, "unit": "GB/s", "passed": 1},
            {"metric_name": "NVLink Bandwidth", "value": 600.0, "unit": "GB/s", "passed": 1},
            {"metric_name": "PCIe Bandwidth", "value": 12.0, "unit": "GB/s", "passed": 1},
            {"metric_name": "Internet Upload", "value": 125.3, "unit": "Mbps", "passed": 1},
            {"metric_name": "Internet Download", "value": 450.1, "unit": "Mbps", "passed": 1},
            {"metric_name": "Disk Seq Read", "value": 3200.0, "unit": "MB/s", "passed": 1},
            {"metric_name": "Disk Seq Write", "value": 2800.0, "unit": "MB/s", "passed": 1},
        ]
    return [{"metric_name": "connectivity", "value": 1.0, "unit": "passed", "passed": 1}]


@router.post("/{instance_id}/tests")
async def trigger_test(instance_id: str, body: TriggerTestRequest, request: Request, _payload: dict = Depends(require_auth)):
    instance = await get_instance(instance_id)
    if instance is None or instance["user_id"] != request.state.user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Instance not found"})
    if instance["status"] != "ready":
        raise HTTPException(status_code=422, detail={"error": "NOT_READY", "message": "Instance must be in ready state"})
    db = await get_db()
    test_run_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO test_runs (id, instance_id, type, status, started_at, trigger) VALUES (?, ?, ?, 'running', datetime('now'), ?)",
        (test_run_id, instance_id, body.type, "manual"),
    )
    mock_results = _generate_mock_results(test_run_id, body.type)
    for r in mock_results:
        await db.execute(
            "INSERT INTO test_results (test_run_id, metric_name, value, unit, passed) VALUES (?, ?, ?, ?, ?)",
            (test_run_id, r["metric_name"], r["value"], r["unit"], r["passed"]),
        )
    await db.execute(
        "UPDATE test_runs SET status = 'completed', finished_at = datetime('now') WHERE id = ?",
        (test_run_id,),
    )
    await db.commit()
    return {"test_run_id": test_run_id, "status": "completed"}


@router.get("/{instance_id}/tests")
async def list_tests(instance_id: str, request: Request, _payload: dict = Depends(require_auth)):
    instance = await get_instance(instance_id)
    if instance is None or instance["user_id"] != request.state.user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Instance not found"})
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM test_runs WHERE instance_id = ? ORDER BY started_at DESC",
        (instance_id,),
    )
    runs = [dict(row) for row in await cursor.fetchall()]
    for run in runs:
        cursor2 = await db.execute(
            "SELECT * FROM test_results WHERE test_run_id = ? ORDER BY id",
            (run["id"],),
        )
        run["results"] = [dict(row) for row in await cursor2.fetchall()]
    return {"test_runs": runs}


@router.get("/{instance_id}/tests/export")
async def export_tests(instance_id: str, request: Request, format: str = Query("json"), _payload: dict = Depends(require_auth)):
    instance = await get_instance(instance_id)
    if instance is None or instance["user_id"] != request.state.user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Instance not found"})
    db = await get_db()
    cursor = await db.execute(
        "SELECT tr.id as run_id, tr.type, tr.started_at, tr.finished_at, "
        "tres.metric_name, tres.value, tres.unit, tres.passed "
        "FROM test_runs tr JOIN test_results tres ON tres.test_run_id = tr.id "
        "WHERE tr.instance_id = ? ORDER BY tr.started_at DESC",
        (instance_id,),
    )
    rows = [dict(row) for row in await cursor.fetchall()]
    return {"results": rows, "format": format}


@router.post("/{instance_id}/connectivity")
async def trigger_connectivity_test(instance_id: str, request: Request, _payload: dict = Depends(require_auth)):
    instance = await get_instance(instance_id)
    if instance is None or instance["user_id"] != request.state.user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Instance not found"})
    db = await get_db()
    targets = [
        ("huggingface.co", 200, 45.2, 1),
        ("cloudflare.com", 200, 5.1, 1),
        ("aws.amazon.com", 200, 120.3, 1),
        ("api.openai.com", 200, 200.5, 1),
        ("google.com", 200, 80.0, 0),
    ]
    for target, status_code, latency, is_direct in targets:
        await db.execute(
            "INSERT INTO connectivity_tests (instance_id, target, status_code, latency_ms, is_direct) VALUES (?, ?, ?, ?, ?)",
            (instance_id, target, status_code, latency, is_direct),
        )
    await db.commit()
    return {"status": "completed", "targets_tested": len(targets)}


@router.get("/{instance_id}/connectivity")
async def get_connectivity(instance_id: str, request: Request, _payload: dict = Depends(require_auth)):
    instance = await get_instance(instance_id)
    if instance is None or instance["user_id"] != request.state.user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Instance not found"})
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM connectivity_tests WHERE instance_id = ? ORDER BY timestamp DESC LIMIT 5",
        (instance_id,),
    )
    rows = [dict(row) for row in await cursor.fetchall()]
    return {"connectivity_tests": rows}
