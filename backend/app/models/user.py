import uuid
import bcrypt
from app.database import get_db


async def create_user(username: str, password: str) -> dict | None:
    db = await get_db()
    user_id = str(uuid.uuid4())
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        await db.execute(
            "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
            (user_id, username, password_hash),
        )
        await db.commit()
        return {"id": user_id, "username": username}
    except Exception:
        return None


async def get_user_by_username(username: str) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = await cursor.fetchone()
    if row is None:
        return None
    return dict(row)


async def verify_password(username: str, password: str) -> dict | None:
    user = await get_user_by_username(username)
    if user is None:
        return None
    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return None
    return {"id": user["id"], "username": user["username"]}
