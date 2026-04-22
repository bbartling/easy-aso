from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import pytest

from easy_aso.supervisor.runtime.registry import SupervisorRuntime
from easy_aso.supervisor.store.database import open_supervisor_db
from easy_aso.supervisor.store.repository import SupervisorRepository
from easy_aso.supervisor.store.seed import ensure_seed_data


def _rpc_call(client, method: str, params: dict, auth_token: str | None = None):
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": method,
        "params": params,
    }
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    r = client.post("/api", json=payload, headers=headers)
    data = r.json()
    assert "error" not in data, data.get("error")
    return r, data["result"]


@pytest.mark.asyncio
async def test_store_seed_and_device_roundtrip(tmp_path: Path) -> None:
    db = tmp_path / "t1.sqlite"
    conn = await open_supervisor_db(str(db))
    repo = SupervisorRepository(conn)
    await ensure_seed_data(repo)
    assert await repo.device_count() >= 1
    devs = await repo.list_devices()
    assert any(d.id == "seed-example-vav" for d in devs)
    d = await repo.get_device("seed-example-vav")
    assert d is not None
    assert d.enabled is False
    pts = await repo.list_points(d.id)
    assert len(pts) >= 2
    await conn.close()


@pytest.mark.asyncio
async def test_runtime_stub_poll_updates_points(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPERVISOR_DB_PATH", str(tmp_path / "t2.sqlite"))
    conn = await open_supervisor_db(str(tmp_path / "t2.sqlite"))
    repo = SupervisorRepository(conn)
    await ensure_seed_data(repo)
    await repo.update_device_fields(
        "seed-example-vav",
        {"enabled": True, "scrape_interval_seconds": 0.35},
    )
    rt = SupervisorRuntime(repo)
    await rt.start()
    try:
        await asyncio.sleep(0.5)
        h = rt.device_health("seed-example-vav")
        assert h is not None
        assert h.last_poll_at is not None
        pts = await repo.list_points("seed-example-vav", enabled_only=True)
        for p in pts:
            assert p.last_polled_at is not None
            assert p.last_error is None
            assert p.last_value_json is not None
    finally:
        await rt.stop()
        await conn.close()


@pytest.mark.asyncio
async def test_hot_reload_on_point_update(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPERVISOR_DB_PATH", str(tmp_path / "t3.sqlite"))
    conn = await open_supervisor_db(str(tmp_path / "t3.sqlite"))
    repo = SupervisorRepository(conn)
    await ensure_seed_data(repo)
    await repo.update_device_fields("seed-example-vav", {"enabled": True, "scrape_interval_seconds": 0.4})
    rt = SupervisorRuntime(repo)
    await rt.start()
    try:
        await asyncio.sleep(0.35)
        pts = await repo.list_points("seed-example-vav")
        pid = pts[0].id
        await repo.update_point_fields(pid, {"name": "renamed"})
        await rt.reload_device("seed-example-vav")
        await asyncio.sleep(0.35)
        h = rt.device_health("seed-example-vav")
        assert h is not None
        assert h.status in ("running", "error")
    finally:
        await rt.stop()
        await conn.close()


def test_supervisor_rpc_crud(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPERVISOR_DB_PATH", str(tmp_path / "t4.sqlite"))
    monkeypatch.delenv("SUPERVISOR_API_KEY", raising=False)
    from starlette.testclient import TestClient

    from easy_aso.supervisor.app import create_supervisor_app

    with TestClient(create_supervisor_app()) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        _, devices0 = _rpc_call(client, "supervisor_list_devices", {"query": {"enabled_only": False}})
        assert isinstance(devices0, list)
        body = {
            "name": "HTTP test device",
            "driver_type": "stub",
            "device_address": "0",
            "scrape_interval_seconds": 2.0,
            "enabled": False,
        }
        _, created_device = _rpc_call(client, "supervisor_create_device", {"payload": body})
        did = created_device["id"]
        _, created_point = _rpc_call(
            client,
            "supervisor_create_point",
            {
                "req": {
                    "device_id": did,
                    "payload": {
                        "name": "p1",
                        "object_identifier": "analog-input,1",
                        "property_identifier": "present-value",
                    },
                }
            },
        )
        _rpc_call(
            client,
            "supervisor_patch_device",
            {"req": {"device_id": did, "payload": {"enabled": True, "scrape_interval_seconds": 0.35}}},
        )
        import time

        time.sleep(0.6)
        _, latest = _rpc_call(client, "supervisor_latest_values", {"req": {"device_id": did}})
        assert len(latest) >= 1
        _, hh = _rpc_call(client, "supervisor_device_health", {"req": {"device_id": did}})
        assert hh["device_id"] == did
        _rpc_call(client, "supervisor_delete_point", {"req": {"point_id": created_point["id"]}})
        _rpc_call(client, "supervisor_delete_device", {"req": {"device_id": did}})


def test_supervisor_rpc_bearer_auth(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPERVISOR_DB_PATH", str(tmp_path / "t5.sqlite"))
    monkeypatch.setenv("SUPERVISOR_API_KEY", "secret-token")
    from starlette.testclient import TestClient

    from easy_aso.supervisor.app import create_supervisor_app

    with TestClient(create_supervisor_app()) as client:
        # exempt path
        health = client.get("/health")
        assert health.status_code == 200

        # protected path
        no_auth = client.post(
            "/api",
            json={"jsonrpc": "2.0", "id": "1", "method": "supervisor_list_devices", "params": {"query": {"enabled_only": False}}},
        )
        assert no_auth.status_code == 401

        bad_auth = client.post(
            "/api",
            json={"jsonrpc": "2.0", "id": "2", "method": "supervisor_list_devices", "params": {"query": {"enabled_only": False}}},
            headers={"Authorization": "Bearer wrong"},
        )
        assert bad_auth.status_code == 403

        ok_auth = _rpc_call(client, "supervisor_list_devices", {"query": {"enabled_only": False}}, auth_token="secret-token")
        assert ok_auth[0].status_code == 200

        openapi = client.get("/openapi.json")
        assert openapi.status_code == 200
        security_schemes = (openapi.json().get("components") or {}).get("securitySchemes") or {}
        assert "BearerAuth" in security_schemes
        health_path = (((openapi.json().get("paths") or {}).get("/health")) or {}).get("get") or {}
        assert health_path.get("security") == []
