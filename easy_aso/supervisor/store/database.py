from __future__ import annotations

from pathlib import Path

import aiosqlite

from .schema import migrate_schema


async def open_supervisor_db(path: str) -> aiosqlite.Connection:
    """Open SQLite (creates parent dirs), apply migrations, return connection."""
    p = Path(path)
    if not path.startswith(":memory:"):
        p.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON")
    await migrate_schema(conn)
    return conn
