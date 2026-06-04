import os
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.database import _db

TEST_DB_PATH = "data/test_schedule.db"


@pytest.fixture(autouse=True)
def setup_test_db_env():
    os.environ["DATABASE_PATH"] = TEST_DB_PATH
    import app.config
    app.config.DATABASE_PATH = TEST_DB_PATH
    yield
    try:
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
        for suffix in ("-wal", "-shm"):
            if os.path.exists(TEST_DB_PATH + suffix):
                os.remove(TEST_DB_PATH + suffix)
    except PermissionError:
        pass


@pytest_asyncio.fixture(autouse=True)
async def reset_db():
    import app.database
    if app.database._db:
        await app.database._db.close()
        app.database._db = None
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    from app.database import get_db
    db = await get_db()
    yield db
    if app.database._db:
        await app.database._db.close()
        app.database._db = None


@pytest_asyncio.fixture
async def client(reset_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(client):
    await client.post("/api/auth/register", json={"username": "testuser", "password": "testpass123"})
    resp = await client.post("/api/auth/login", json={"username": "testuser", "password": "testpass123"})
    token = resp.json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest_asyncio.fixture
async def raw_client(reset_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
