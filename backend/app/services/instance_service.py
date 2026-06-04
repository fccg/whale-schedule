import asyncio
import logging
from app.models.instance import update_instance_status, get_instance

logger = logging.getLogger(__name__)


async def advance_instance_lifecycle(instance_id: str):
    """Event-driven lifecycle bootstrap simulation.

    When a real agent is not yet connected, this simulates the bootstrap→testing→ready
    progression with modest delays. Each state transition is recorded so that when a
    real agent heartbeat arrives, it takes over.
    """
    steps = [
        ("provisioning", 1, 10),
        ("bootstrapping", 2, 40),
        ("bootstrapping", 3, 60),
        ("bootstrapping", 4, 80),
        ("testing", 5, 90),
        ("ready", 6, 100),
    ]
    for status, step, progress in steps:
        inst = await get_instance(instance_id)
        if inst is None:
            break
        # Don't override if a real agent has already advanced the state
        current_status = inst.get("status", "provisioning")
        if current_status in ("ready", "degraded", "failed", "destroyed"):
            break
        if current_status == "testing" and status in ("provisioning", "bootstrapping"):
            continue
        await asyncio.sleep(2)
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
