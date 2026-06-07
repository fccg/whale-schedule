import pytest


@pytest.mark.asyncio
async def test_budget_is_per_user(client):
    await client.post("/api/auth/register", json={"username": "buser1", "password": "pass123456"})
    r1 = await client.post("/api/auth/login", json={"username": "buser1", "password": "pass123456"})
    t1 = r1.json()["token"]

    await client.post("/api/auth/register", json={"username": "buser2", "password": "pass123456"})
    r2 = await client.post("/api/auth/login", json={"username": "buser2", "password": "pass123456"})
    t2 = r2.json()["token"]

    client.headers["Authorization"] = f"Bearer {t1}"
    resp = await client.get("/api/budget")
    assert resp.json()["remaining"] == 100.0

    client.headers["Authorization"] = f"Bearer {t2}"
    resp = await client.get("/api/budget")
    assert resp.json()["remaining"] == 100.0


@pytest.mark.asyncio
async def test_provider_budget_remaining_and_logs(reset_db):
    from app.database import get_db
    from app.services.budget_service import (
        check_provider_budget,
        get_provider_budget_remaining,
        log_provider_budget,
    )

    assert await get_provider_budget_remaining("autodl") is None
    assert await check_provider_budget("autodl", 10.0) is None

    db = await get_db()
    await db.execute(
        """
        INSERT INTO provider_budget_configs (provider, total_budget, currency, enabled)
        VALUES (?, ?, ?, ?)
        """,
        ("autodl", 20.0, "CNY", 1),
    )
    await db.commit()

    assert await get_provider_budget_remaining("autodl") == 20.0
    assert await check_provider_budget("autodl", 10.0) is True

    await log_provider_budget("u1", "i1", "autodl", "create", 8.5)
    assert await get_provider_budget_remaining("autodl") == 11.5
    assert await check_provider_budget("autodl", 12.0) is False
