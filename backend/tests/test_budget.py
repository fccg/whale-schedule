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
