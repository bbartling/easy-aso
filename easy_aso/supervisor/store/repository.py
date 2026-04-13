from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional, Sequence

import aiosqlite

from .models import Device, Point


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def _row_device(row: aiosqlite.Row) -> Device:
    return Device(
        id=row["id"],
        name=row["name"],
        driver_type=row["driver_type"],
        device_address=row["device_address"],
        rpc_base_url=row["rpc_base_url"],
        rpc_entrypoint=row["rpc_entrypoint"],
        scrape_interval_seconds=float(row["scrape_interval_seconds"]),
        enabled=bool(row["enabled"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_point(row: aiosqlite.Row) -> Point:
    return Point(
        id=row["id"],
        device_id=row["device_id"],
        name=row["name"] or "",
        object_identifier=row["object_identifier"],
        property_identifier=row["property_identifier"],
        enabled=bool(row["enabled"]),
        last_value_json=row["last_value_json"],
        last_polled_at=row["last_polled_at"],
        last_error=row["last_error"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class SupervisorRepository:
    """Async CRUD for devices and points (single connection, serialized writes)."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn
        self._lock = asyncio.Lock()

    @property
    def connection(self) -> aiosqlite.Connection:
        return self._conn

    async def device_count(self) -> int:
        async with self._lock:
            async with self._conn.execute("SELECT COUNT(*) AS c FROM devices") as cur:
                row = await cur.fetchone()
        return int(row["c"]) if row else 0

    async def list_devices(self, *, enabled_only: bool = False) -> List[Device]:
        sql = "SELECT * FROM devices"
        if enabled_only:
            sql += " WHERE enabled = 1"
        sql += " ORDER BY name"
        async with self._lock:
            async with self._conn.execute(sql) as cur:
                rows = await cur.fetchall()
        return [_row_device(r) for r in rows]

    async def get_device(self, device_id: str) -> Optional[Device]:
        async with self._lock:
            async with self._conn.execute("SELECT * FROM devices WHERE id = ?", (device_id,)) as cur:
                row = await cur.fetchone()
        return _row_device(row) if row else None

    async def create_device(
        self,
        *,
        name: str,
        driver_type: str,
        device_address: str,
        rpc_base_url: Optional[str] = None,
        rpc_entrypoint: Optional[str] = None,
        scrape_interval_seconds: float = 5.0,
        enabled: bool = False,
        device_id: Optional[str] = None,
    ) -> Device:
        now = _utc_iso()
        did = device_id or _new_id()
        async with self._lock:
            await self._conn.execute(
                """
                INSERT INTO devices (
                  id, name, driver_type, device_address, rpc_base_url, rpc_entrypoint,
                  scrape_interval_seconds, enabled, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    did,
                    name,
                    driver_type,
                    device_address,
                    rpc_base_url,
                    rpc_entrypoint,
                    scrape_interval_seconds,
                    int(enabled),
                    now,
                    now,
                ),
            )
            await self._conn.commit()
        out = await self.get_device(did)
        assert out is not None
        return out

    async def update_device_fields(self, device_id: str, fields: dict[str, Any]) -> Optional[Device]:
        """Patch device columns; only keys present in ``fields`` are updated."""
        cur_dev = await self.get_device(device_id)
        if cur_dev is None:
            return None
        name = fields.get("name", cur_dev.name)
        driver_type = fields.get("driver_type", cur_dev.driver_type)
        device_address = fields.get("device_address", cur_dev.device_address)
        rpc_base_url = fields.get("rpc_base_url", cur_dev.rpc_base_url)
        rpc_entrypoint = fields.get("rpc_entrypoint", cur_dev.rpc_entrypoint)
        scrape_interval_seconds = fields.get("scrape_interval_seconds", cur_dev.scrape_interval_seconds)
        enabled = fields.get("enabled", cur_dev.enabled)
        now = _utc_iso()
        async with self._lock:
            await self._conn.execute(
                """
                UPDATE devices SET
                  name = ?, driver_type = ?, device_address = ?, rpc_base_url = ?, rpc_entrypoint = ?,
                  scrape_interval_seconds = ?, enabled = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    name,
                    driver_type,
                    device_address,
                    rpc_base_url,
                    rpc_entrypoint,
                    scrape_interval_seconds,
                    int(enabled),
                    now,
                    device_id,
                ),
            )
            await self._conn.commit()
        return await self.get_device(device_id)

    async def delete_device(self, device_id: str) -> bool:
        async with self._lock:
            cur = await self._conn.execute("DELETE FROM devices WHERE id = ?", (device_id,))
            deleted = cur.rowcount
            await self._conn.commit()
        return deleted > 0

    async def list_points(self, device_id: str, *, enabled_only: bool = False) -> List[Point]:
        sql = "SELECT * FROM points WHERE device_id = ?"
        params: Sequence[Any] = (device_id,)
        if enabled_only:
            sql += " AND enabled = 1"
        sql += " ORDER BY name, object_identifier"
        async with self._lock:
            async with self._conn.execute(sql, params) as cur:
                rows = await cur.fetchall()
        return [_row_point(r) for r in rows]

    async def get_point(self, point_id: str) -> Optional[Point]:
        async with self._lock:
            async with self._conn.execute("SELECT * FROM points WHERE id = ?", (point_id,)) as cur:
                row = await cur.fetchone()
        return _row_point(row) if row else None

    async def create_point(
        self,
        device_id: str,
        *,
        name: str = "",
        object_identifier: str,
        property_identifier: str = "present-value",
        enabled: bool = True,
        point_id: Optional[str] = None,
    ) -> Point:
        now = _utc_iso()
        pid = point_id or _new_id()
        async with self._lock:
            await self._conn.execute(
                """
                INSERT INTO points (
                  id, device_id, name, object_identifier, property_identifier, enabled,
                  last_value_json, last_polled_at, last_error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?)
                """,
                (pid, device_id, name, object_identifier, property_identifier, int(enabled), now, now),
            )
            await self._conn.commit()
        out = await self.get_point(pid)
        assert out is not None
        return out

    async def update_point_fields(self, point_id: str, fields: dict[str, Any]) -> Optional[Point]:
        cur = await self.get_point(point_id)
        if cur is None:
            return None
        name = fields.get("name", cur.name)
        object_identifier = fields.get("object_identifier", cur.object_identifier)
        property_identifier = fields.get("property_identifier", cur.property_identifier)
        enabled = fields.get("enabled", cur.enabled)
        now = _utc_iso()
        async with self._lock:
            await self._conn.execute(
                """
                UPDATE points SET
                  name = ?, object_identifier = ?, property_identifier = ?, enabled = ?, updated_at = ?
                WHERE id = ?
                """,
                (name, object_identifier, property_identifier, int(enabled), now, point_id),
            )
            await self._conn.commit()
        return await self.get_point(point_id)

    async def delete_point(self, point_id: str) -> bool:
        async with self._lock:
            cur = await self._conn.execute("DELETE FROM points WHERE id = ?", (point_id,))
            deleted = cur.rowcount
            await self._conn.commit()
        return deleted > 0

    async def update_point_reading(
        self,
        point_id: str,
        *,
        value: Any,
        polled_at: str,
        error: Optional[str],
    ) -> None:
        if value is None:
            payload = None
        else:
            payload = json.dumps(value)
        async with self._lock:
            await self._conn.execute(
                """
                UPDATE points SET
                  last_value_json = ?, last_polled_at = ?, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (payload, polled_at, error, polled_at, point_id),
            )
            await self._conn.commit()
