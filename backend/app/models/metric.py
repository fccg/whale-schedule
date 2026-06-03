from app.database import get_db


async def insert_metric(
    instance_id: str,
    cpu_percent: float | None = None,
    memory_percent: float | None = None,
    memory_used_gb: float | None = None,
    memory_total_gb: float | None = None,
    gpu_util_percent: float | None = None,
    gpu_vram_percent: float | None = None,
    disk_used_gb: float | None = None,
    disk_total_gb: float | None = None,
    net_up_mbps: float | None = None,
    net_down_mbps: float | None = None,
    gpu_json: str | None = None,
):
    db = await get_db()
    await db.execute(
        """INSERT INTO metrics (instance_id, cpu_percent, memory_percent,
           memory_used_gb, memory_total_gb, gpu_util_percent, gpu_vram_percent,
           disk_used_gb, disk_total_gb, net_up_mbps, net_down_mbps, gpu_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (instance_id, cpu_percent, memory_percent, memory_used_gb,
         memory_total_gb, gpu_util_percent, gpu_vram_percent, disk_used_gb,
         disk_total_gb, net_up_mbps, net_down_mbps, gpu_json),
    )
    await db.commit()


async def get_latest_metrics(instance_id: str) -> dict | None:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM metrics WHERE instance_id = ? ORDER BY timestamp DESC LIMIT 1",
        (instance_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_metrics_history(instance_id: str, limit: int = 60) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM metrics WHERE instance_id = ? ORDER BY timestamp DESC LIMIT ?",
        (instance_id, limit),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in reversed(rows)]
