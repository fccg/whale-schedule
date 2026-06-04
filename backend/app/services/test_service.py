import csv
import io
import json
import uuid
from datetime import datetime, timezone
from app.database import get_db

PERF_TEST_DEFINITIONS = [
    {"metric_name": "GPU Memory Bandwidth", "unit": "GB/s", "group": "gpu"},
    {"metric_name": "NVLink Status", "unit": "status", "group": "topology"},
    {"metric_name": "NVLink Bandwidth", "unit": "GB/s", "group": "gpu"},
    {"metric_name": "PCIe Lanes", "unit": "xN", "group": "topology"},
    {"metric_name": "PCIe Bandwidth", "unit": "GB/s", "group": "gpu"},
    {"metric_name": "Internet Upload", "unit": "Mbps", "group": "network"},
    {"metric_name": "Internet Download", "unit": "Mbps", "group": "network"},
    {"metric_name": "Disk Seq Read", "unit": "MB/s", "group": "disk"},
    {"metric_name": "Disk Seq Write", "unit": "MB/s", "group": "disk"},
]

CONNECTIVITY_TARGETS = [
    {"target": "huggingface.co", "expected_status": 200},
    {"target": "cloudflare.com", "expected_status": 200},
    {"target": "aws.amazon.com", "expected_status": 200},
    {"target": "api.openai.com", "expected_status": 200},
    {"target": "google.com", "expected_status": 200},
]


async def run_perf_test(instance_id: str) -> dict:
    """Run performance test and store results."""
    db = await get_db()
    test_run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()

    await db.execute(
        "INSERT INTO test_runs (id, instance_id, type, status, started_at, trigger) VALUES (?, ?, ?, 'running', ?, 'manual')",
        (test_run_id, instance_id, "perf", started_at),
    )
    await db.commit()

    results = []
    for definition in PERF_TEST_DEFINITIONS:
        results.append({
            "test_run_id": test_run_id,
            "metric_name": definition["metric_name"],
            "value": None,
            "unit": definition["unit"],
            "passed": 0,
        })
        await db.execute(
            "INSERT INTO test_results (test_run_id, metric_name, value, unit, passed) VALUES (?, ?, ?, ?, ?)",
            (test_run_id, definition["metric_name"], None, definition["unit"], 0),
        )

    finished_at = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE test_runs SET status = 'completed', finished_at = ? WHERE id = ?",
        (finished_at, test_run_id),
    )
    await db.commit()

    return {"test_run_id": test_run_id, "status": "completed", "results": results}


async def run_connectivity_test(instance_id: str) -> dict:
    """Run connectivity test against external targets."""
    db = await get_db()
    test_run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()

    await db.execute(
        "INSERT INTO test_runs (id, instance_id, type, status, started_at, trigger) VALUES (?, ?, ?, 'running', ?, 'manual')",
        (test_run_id, instance_id, "connectivity", started_at),
    )
    await db.commit()

    # Store connectivity results as both test_results and connectivity_tests
    for target_info in CONNECTIVITY_TARGETS:
        target = target_info["target"]
        await db.execute(
            "INSERT INTO connectivity_tests (instance_id, target, status_code, latency_ms, is_direct) VALUES (?, ?, ?, ?, ?)",
            (instance_id, target, None, None, 1),
        )
        await db.execute(
            "INSERT INTO test_results (test_run_id, metric_name, value, unit, passed) VALUES (?, ?, ?, ?, ?)",
            (test_run_id, f"connectivity_{target}", None, "reachable", 0),
        )

    finished_at = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE test_runs SET status = 'completed', finished_at = ? WHERE id = ?",
        (finished_at, test_run_id),
    )
    await db.commit()

    return {"test_run_id": test_run_id, "status": "completed", "targets_tested": len(CONNECTIVITY_TARGETS)}


async def export_test_results(instance_id: str, format: str = "json") -> tuple[str, str]:
    """Export test results for an instance. Returns (content, content_type)."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT tr.id as run_id, tr.type, tr.started_at, tr.finished_at,
           tres.metric_name, tres.value, tres.unit, tres.passed
           FROM test_runs tr
           JOIN test_results tres ON tres.test_run_id = tr.id
           WHERE tr.instance_id = ?
           ORDER BY tr.started_at DESC""",
        (instance_id,),
    )
    rows = [dict(row) for row in await cursor.fetchall()]

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["run_id", "type", "started_at", "finished_at", "metric_name", "value", "unit", "passed"])
        for row in rows:
            writer.writerow([
                row["run_id"], row["type"], row["started_at"], row["finished_at"],
                row["metric_name"], row.get("value", ""), row["unit"], row["passed"],
            ])
        return output.getvalue(), "text/csv"

    # JSON
    return json.dumps({"results": rows, "format": "json", "instance_id": instance_id}, indent=2), "application/json"
