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
