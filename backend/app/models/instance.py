import uuid
from app.database import get_db


async def create_instance(
    user_id: str,
    provider: str,
    gpu_offering_id: str,
    config_json: str,
    agent_token: str,
    provider_instance_id: str | None = None,
) -> dict:
    db = await get_db()
    instance_id = str(uuid.uuid4())
    await db.execute(
        """INSERT INTO instances (id, user_id, provider, provider_instance_id,
           gpu_offering_id, config_json, agent_token)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (instance_id, user_id, provider, provider_instance_id,
         gpu_offering_id, config_json, agent_token),
    )
    await db.commit()
    return await get_instance(instance_id)


async def get_instance(instance_id: str) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM instances WHERE id = ?", (instance_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_user_instances(user_id: str) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM instances WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    )
    return [dict(row) for row in await cursor.fetchall()]


async def update_instance_status(
    instance_id: str,
    status: str,
    current_step: int | None = None,
    progress_percent: float | None = None,
    last_error: str | None = None,
):
    db = await get_db()
    parts = ["status = ?"]
    params: list = [status]
    if current_step is not None:
        parts.append("current_step = ?")
        params.append(current_step)
    if progress_percent is not None:
        parts.append("progress_percent = ?")
        params.append(progress_percent)
    if last_error is not None:
        parts.append("last_error = ?")
        params.append(last_error)
    params.append(instance_id)
    await db.execute(
        f"UPDATE instances SET {', '.join(parts)} WHERE id = ?", params
    )
    await db.commit()


async def update_heartbeat(instance_id: str):
    db = await get_db()
    await db.execute(
        "UPDATE instances SET last_heartbeat_at = datetime('now') WHERE id = ?",
        (instance_id,),
    )
    await db.commit()


async def destroy_instance(instance_id: str):
    db = await get_db()
    await db.execute(
        "UPDATE instances SET destroyed_at = datetime('now'), status = 'destroyed' WHERE id = ?",
        (instance_id,),
    )
    await db.commit()
