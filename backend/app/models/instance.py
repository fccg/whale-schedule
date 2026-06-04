import json
import uuid
from app.database import get_db


async def create_instance(
    user_id: str,
    provider: str,
    gpu_offering_id: str,
    config_json: str,
    agent_token: str,
    provider_instance_id: str | None = None,
    display_name: str | None = None,
    hourly_price: float | None = None,
    region: str | None = None,
    ssh_host: str | None = None,
    ssh_port: int | None = None,
    connect_url: str | None = None,
    jupyter_url: str | None = None,
    metadata_json: str | None = None,
) -> dict:
    db = await get_db()
    instance_id = str(uuid.uuid4())
    await db.execute(
        """INSERT INTO instances (id, user_id, provider, provider_instance_id,
           gpu_offering_id, config_json, agent_token, display_name, hourly_price,
           region, ssh_host, ssh_port, connect_url, jupyter_url, metadata_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (instance_id, user_id, provider, provider_instance_id,
         gpu_offering_id, config_json, agent_token, display_name, hourly_price,
         region, ssh_host, ssh_port, connect_url, jupyter_url, metadata_json or "{}"),
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
    clear_error: bool = False,
    ssh_host: str | None = None,
    ssh_port: int | None = None,
    connect_url: str | None = None,
    jupyter_url: str | None = None,
    hourly_price: float | None = None,
    region: str | None = None,
    display_name: str | None = None,
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
    if clear_error:
        parts.append("last_error = NULL")
    elif last_error is not None:
        parts.append("last_error = ?")
        params.append(last_error)
    if ssh_host is not None:
        parts.append("ssh_host = ?")
        params.append(ssh_host)
    if ssh_port is not None:
        parts.append("ssh_port = ?")
        params.append(ssh_port)
    if connect_url is not None:
        parts.append("connect_url = ?")
        params.append(connect_url)
    if jupyter_url is not None:
        parts.append("jupyter_url = ?")
        params.append(jupyter_url)
    if hourly_price is not None:
        parts.append("hourly_price = ?")
        params.append(hourly_price)
    if region is not None:
        parts.append("region = ?")
        params.append(region)
    if display_name is not None:
        parts.append("display_name = ?")
        params.append(display_name)
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
