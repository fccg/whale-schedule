import pytest


@pytest.mark.asyncio
async def test_register_and_login(auth_client):
    resp = await auth_client.get("/api/auth/check")
    assert resp.status_code == 200
    assert resp.json()["username"] == "testuser"


@pytest.mark.asyncio
async def test_register_duplicate(client):
    await client.post("/api/auth/register", json={"username": "dup", "password": "testpass123"})
    resp = await client.post("/api/auth/register", json={"username": "dup", "password": "testpass123"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_bad_password(client):
    await client.post("/api/auth/register", json={"username": "u1", "password": "testpass123"})
    resp = await client.post("/api/auth/login", json={"username": "u1", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated(client):
    resp = await client.get("/api/gpus")
    assert resp.status_code == 401
