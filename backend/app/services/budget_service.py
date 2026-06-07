from app.config import DEFAULT_BUDGET
from app.database import get_db


async def get_remaining_budget(user_id: str) -> float:
    db = await get_db()
    cursor = await db.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM budget_logs WHERE user_id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    spent = row[0] if row else 0.0
    return max(0.0, DEFAULT_BUDGET - spent)


async def check_budget(user_id: str, estimated_cost: float) -> bool:
    remaining = await get_remaining_budget(user_id)
    return estimated_cost <= remaining


async def log_budget(user_id: str, instance_id: str, action: str, amount: float):
    db = await get_db()
    await db.execute(
        "INSERT INTO budget_logs (user_id, instance_id, action, amount) VALUES (?, ?, ?, ?)",
        (user_id, instance_id, action, amount),
    )
    await db.commit()


async def get_provider_budget_config(provider: str) -> dict | None:
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT provider, total_budget, currency, enabled, created_at, updated_at
        FROM provider_budget_configs
        WHERE provider = ?
        """,
        (provider,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_provider_budget_remaining(provider: str) -> float | None:
    config = await get_provider_budget_config(provider)
    if config is None or config.get("enabled", 1) == 0 or config.get("total_budget") is None:
        return None

    db = await get_db()
    cursor = await db.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM provider_budget_logs WHERE provider = ?",
        (provider,),
    )
    row = await cursor.fetchone()
    spent = float(row[0] if row else 0.0)
    total_budget = float(config["total_budget"])
    return max(0.0, total_budget - spent)


async def check_provider_budget(provider: str, estimated_cost: float) -> bool | None:
    remaining = await get_provider_budget_remaining(provider)
    if remaining is None:
        return None
    return estimated_cost <= remaining


async def log_provider_budget(user_id: str, instance_id: str, provider: str, action: str, amount: float):
    config = await get_provider_budget_config(provider)
    currency = config.get("currency", "CNY") if config else "CNY"

    db = await get_db()
    await db.execute(
        """
        INSERT INTO provider_budget_logs (user_id, instance_id, provider, action, amount, currency)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, instance_id, provider, action, amount, currency),
    )
    await db.commit()
