import asyncio
import random
from app.models.instance import update_instance_status, get_instance


async def advance_instance_lifecycle(instance_id: str):
    """Mock lifecycle: provisioning(5s) -> bootstrapping(5s) -> testing(5s) -> ready
    With 10% random failure at bootstrapping steps 3-4 for error-path demo."""
    steps = [
        ("provisioning", 1, 10, None),
        ("bootstrapping", 2, 40, None),
        ("bootstrapping", 3, 60, None),
        ("bootstrapping", 4, 80, None),
        ("testing", 5, 90, None),
        ("ready", 6, 100, None),
    ]
    for status, step, progress, _ in steps:
        await asyncio.sleep(3)
        if status == "bootstrapping" and step in (3, 4) and random.random() < 0.10:
            await update_instance_status(
                instance_id,
                status="failed",
                current_step=step,
                progress_percent=float(progress),
                last_error=f"Environment setup failed at step {step}: simulated error",
            )
            return
        await update_instance_status(
            instance_id,
            status=status,
            current_step=step,
            progress_percent=float(progress),
        )


def start_lifecycle_advance(instance_id: str):
    asyncio.create_task(advance_instance_lifecycle(instance_id))


async def check_degraded_instances():
    """Transition ready -> degraded for instances with no heartbeat in 30s."""
    from app.database import get_db as _get_db
    db = await _get_db()
    cursor = await db.execute(
        """SELECT id FROM instances
           WHERE status = 'ready'
           AND last_heartbeat_at IS NOT NULL
           AND datetime(last_heartbeat_at) < datetime('now', '-30 seconds')"""
    )
    rows = await cursor.fetchall()
    for row in rows:
        await update_instance_status(
            row["id"],
            status="degraded",
            last_error="Heartbeat timeout: no heartbeat received for 30+ seconds",
        )
