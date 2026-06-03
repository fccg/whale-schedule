import os
import aiosqlite
from app.config import DATABASE_PATH

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        _db = await aiosqlite.connect(DATABASE_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.executescript(SCHEMA)
        await _db.commit()
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
"""
