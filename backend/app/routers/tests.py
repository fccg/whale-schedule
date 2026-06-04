from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from app.middleware.auth import require_auth
from app.models.instance import get_instance
from app.database import get_db
from app.services.test_service import run_perf_test, run_connectivity_test, export_test_results

router = APIRouter(prefix="/api/instances", tags=["tests"])


class TriggerTestRequest(BaseModel):
    type: str  # "perf" or "connectivity"


@router.post("/{instance_id}/tests")
async def trigger_test(instance_id: str, body: TriggerTestRequest, request: Request, _payload: dict = Depends(require_auth)):
    instance = await get_instance(instance_id)
    if instance is None or instance["user_id"] != request.state.user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Instance not found"})
    if instance["status"] != "ready":
        raise HTTPException(status_code=422, detail={
            "error": "NOT_READY",
            "message": "Instance must be in ready state",
        })

    if body.type == "perf":
        result = await run_perf_test(instance_id)
    elif body.type == "connectivity":
        result = await run_connectivity_test(instance_id)
    else:
        raise HTTPException(status_code=400, detail={
            "error": "INVALID_TYPE",
            "message": "Type must be 'perf' or 'connectivity'",
        })

    return result


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
async def export_tests(
    instance_id: str,
    request: Request,
    format: str = Query("json"),
    _payload: dict = Depends(require_auth),
):
    instance = await get_instance(instance_id)
    if instance is None or instance["user_id"] != request.state.user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Instance not found"})

    if format not in ("json", "csv"):
        raise HTTPException(status_code=400, detail={
            "error": "INVALID_FORMAT",
            "message": "Format must be 'json' or 'csv'",
        })

    content, content_type = await export_test_results(instance_id, format)
    filename = f"test_results_{instance_id[:8]}.{format}"
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{instance_id}/connectivity")
async def trigger_connectivity_test(instance_id: str, request: Request, _payload: dict = Depends(require_auth)):
    instance = await get_instance(instance_id)
    if instance is None or instance["user_id"] != request.state.user_id:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Instance not found"})

    result = await run_connectivity_test(instance_id)
    return result


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
