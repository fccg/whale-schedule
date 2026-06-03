from app.database import get_db


async def get_gpu_offerings(
    family: str | None = None,
    provider: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    available_only: bool = True,
) -> list[dict]:
    db = await get_db()
    query = "SELECT * FROM gpu_offerings WHERE 1=1"
    params: list = []
    if family:
        query += " AND gpu_family = ?"
        params.append(family)
    if provider:
        query += " AND provider = ?"
        params.append(provider)
    if min_price is not None:
        query += " AND price_per_hour >= ?"
        params.append(min_price)
    if max_price is not None:
        query += " AND price_per_hour <= ?"
        params.append(max_price)
    if available_only:
        query += " AND available = 1"
    query += " ORDER BY price_per_hour ASC"
    cursor = await db.execute(query, params)
    return [dict(row) for row in await cursor.fetchall()]


async def get_gpu_offering(offering_id: str) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM gpu_offerings WHERE id = ?", (offering_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def seed_mock_offerings():
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) FROM gpu_offerings")
    count = (await cursor.fetchone())[0]
    if count > 0:
        return
    mock_data = [
        ("mock-a100-1", "mock", "A100", "A100-80G", 80.0, 16, 128.0, 500.0, 8.50, "CNY", "Beijing"),
        ("mock-a100-2", "mock", "A100", "A100-40G", 40.0, 12, 96.0, 400.0, 6.80, "CNY", "Shanghai"),
        ("mock-h800-1", "mock", "H", "H800-80G", 80.0, 32, 256.0, 1000.0, 12.00, "CNY", "Beijing"),
        ("mock-h800-2", "mock", "H", "H800-80G", 80.0, 32, 256.0, 800.0, 11.50, "CNY", "Shenzhen"),
        ("mock-h100-1", "mock", "H", "H100-80G", 80.0, 32, 256.0, 1000.0, 15.00, "CNY", "Beijing"),
        ("mock-6090-1", "mock", "6090", "RTX 6090", 48.0, 16, 128.0, 500.0, 4.50, "CNY", "Hangzhou"),
        ("mock-6090-2", "mock", "6090", "RTX 6090", 48.0, 16, 128.0, 500.0, 4.20, "CNY", "Guangzhou"),
    ]
    for row in mock_data:
        await db.execute(
            """INSERT INTO gpu_offerings (id, provider, gpu_family, gpu_model,
               vram_gb, cpu_cores, memory_gb, disk_gb, price_per_hour, currency, region)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            row,
        )
    await db.commit()
