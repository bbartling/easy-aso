from __future__ import annotations

import aiosqlite

# Bump when adding migrations (simple PRAGMA user_version ladder).
SCHEMA_VERSION = 1

DDL_V1 = """
CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    driver_type TEXT NOT NULL,
    device_address TEXT NOT NULL,
    rpc_base_url TEXT,
    rpc_entrypoint TEXT,
    scrape_interval_seconds REAL NOT NULL DEFAULT 5.0,
    enabled INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS points (
    id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    object_identifier TEXT NOT NULL,
    property_identifier TEXT NOT NULL DEFAULT 'present-value',
    enabled INTEGER NOT NULL DEFAULT 1,
    last_value_json TEXT,
    last_polled_at TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_points_device_id ON points(device_id);
"""


async def migrate_schema(conn: aiosqlite.Connection) -> None:
    async with conn.execute("PRAGMA user_version") as cur:
        row = await cur.fetchone()
    version = int(row[0]) if row is not None else 0
    if version < 1:
        await conn.executescript(DDL_V1)
        await conn.execute("PRAGMA user_version = 1")
        await conn.commit()
    elif version > SCHEMA_VERSION:
        raise RuntimeError(f"Database schema version {version} is newer than supported {SCHEMA_VERSION}")
    else:
        return
