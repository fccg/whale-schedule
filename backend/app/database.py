import logging
import os
import aiosqlite

logger = logging.getLogger(__name__)

_db: aiosqlite.Connection | None = None


def _get_db_path() -> str:
    return os.getenv("DATABASE_PATH", "data/schedule.db")


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        db_path = _get_db_path()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        _db = await aiosqlite.connect(db_path)
        _db.row_factory = aiosqlite.Row
        await _db.executescript(SCHEMA)
        await _db.commit()
        for migration in MIGRATIONS:
            try:
                await _db.execute(migration)
                await _db.commit()
            except Exception as e:
                msg = str(e).lower()
                if any(hint in msg for hint in ("duplicate column", "already exists")):
                    logger.info("Migration already applied, skipping: %s", migration[:80])
                else:
                    logger.warning("Migration failed, skipping: %s", migration[:80], exc_info=True)
    return _db


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    username    TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS gpu_offerings (
    id              TEXT PRIMARY KEY,
    provider        TEXT NOT NULL,
    gpu_family      TEXT NOT NULL,
    gpu_model       TEXT NOT NULL,
    vram_gb         REAL NOT NULL,
    cpu_cores       INTEGER NOT NULL,
    memory_gb       REAL NOT NULL,
    disk_gb         REAL NOT NULL,
    price_per_hour  REAL NOT NULL,
    currency        TEXT DEFAULT 'CNY',
    region          TEXT,
    available       INTEGER DEFAULT 1,
    metadata_json   TEXT DEFAULT '{}',
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS instances (
    id                  TEXT PRIMARY KEY,
    user_id             TEXT NOT NULL,
    provider            TEXT NOT NULL,
    provider_instance_id TEXT,
    gpu_offering_id     TEXT,
    status              TEXT DEFAULT 'provisioning',
    current_step        INTEGER DEFAULT 0,
    progress_percent    REAL DEFAULT 0,
    last_error          TEXT,
    agent_token         TEXT,
    last_heartbeat_at   TEXT,
    display_name        TEXT,
    hourly_price        REAL,
    region              TEXT,
    ssh_host            TEXT,
    ssh_port            INTEGER,
    connect_url         TEXT,
    jupyter_url         TEXT,
    metadata_json       TEXT DEFAULT '{}',
    config_json         TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    destroyed_at        TEXT
);

CREATE TABLE IF NOT EXISTS metrics (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id      TEXT NOT NULL,
    timestamp        TEXT DEFAULT (datetime('now')),
    cpu_percent      REAL,
    memory_percent   REAL,
    memory_used_gb   REAL,
    memory_total_gb  REAL,
    gpu_util_percent REAL,
    gpu_vram_percent REAL,
    disk_used_gb     REAL,
    disk_total_gb    REAL,
    net_up_mbps      REAL,
    net_down_mbps    REAL,
    gpu_json         TEXT
);

CREATE TABLE IF NOT EXISTS test_runs (
    id          TEXT PRIMARY KEY,
    instance_id TEXT NOT NULL,
    type        TEXT NOT NULL,
    status      TEXT DEFAULT 'running',
    started_at  TEXT,
    finished_at TEXT,
    trigger     TEXT DEFAULT 'manual'
);

CREATE TABLE IF NOT EXISTS test_results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    test_run_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    value       REAL,
    unit        TEXT,
    passed      INTEGER
);

CREATE TABLE IF NOT EXISTS connectivity_tests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id   TEXT NOT NULL,
    target        TEXT NOT NULL,
    status_code   INTEGER,
    latency_ms    REAL,
    is_direct     INTEGER,
    error_message TEXT,
    timestamp     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS budget_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    instance_id TEXT,
    action      TEXT NOT NULL,
    amount      REAL NOT NULL,
    currency    TEXT DEFAULT 'CNY',
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS provider_configs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    provider    TEXT NOT NULL UNIQUE,
    api_base    TEXT,
    enabled     INTEGER DEFAULT 1,
    created_at  TEXT DEFAULT (datetime('now'))
);
"""

MIGRATIONS = [
    "ALTER TABLE gpu_offerings ADD COLUMN metadata_json TEXT DEFAULT '{}'",
    "ALTER TABLE instances ADD COLUMN display_name TEXT",
    "ALTER TABLE instances ADD COLUMN hourly_price REAL",
    "ALTER TABLE instances ADD COLUMN region TEXT",
    "ALTER TABLE instances ADD COLUMN ssh_host TEXT",
    "ALTER TABLE instances ADD COLUMN ssh_port INTEGER",
    "ALTER TABLE instances ADD COLUMN connect_url TEXT",
    "ALTER TABLE instances ADD COLUMN jupyter_url TEXT",
    "ALTER TABLE instances ADD COLUMN metadata_json TEXT DEFAULT '{}'",
    "UPDATE gpu_offerings SET gpu_family = 'A' WHERE gpu_family IN ('A100', 'A800', 'A40', 'A5000', 'A6000')",
    "UPDATE gpu_offerings SET gpu_family = 'H' WHERE gpu_family IN ('H100', 'H800', 'H20')",
    "UPDATE gpu_offerings SET gpu_family = 'RTX' WHERE gpu_family IN ('4090', '5090', '6090', 'RTX 4090', 'RTX 5090', 'RTX 6090', 'RTX 6000 PRO', 'PRO6000')",
]
