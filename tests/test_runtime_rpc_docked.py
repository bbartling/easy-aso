"""Tests for RPC-docked EasyASO runtime, env config, runner, and CLI."""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

from easy_aso.runtime.env import BacnetRpcConfig, load_rpc_config_from_env
from easy_aso.runtime.rpc_docked import RpcDockedEasyASO


def _no_server_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--no-bacnet-server", action="store_true")
    return p.parse_args(["--no-bacnet-server"])


class _StubRpcDocked(RpcDockedEasyASO):
    async def on_start(self) -> None:
        pass

    async def on_step(self) -> None:
        pass

    async def on_stop(self) -> None:
        await self.close_rpc_dock()


def test_load_rpc_config_from_env_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPERVISOR_BACNET_RPC_URL", raising=False)
    monkeypatch.delenv("SUPERVISOR_BACNET_RPC_ENTRYPOINT", raising=False)
    monkeypatch.delenv("BACNET_RPC_API_KEY", raising=False)
    cfg = load_rpc_config_from_env()
    assert cfg.base_url == "http://127.0.0.1:8080"
    assert cfg.entrypoint == "/api"
    assert cfg.bearer_token is None


def test_load_rpc_config_from_env_custom(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPERVISOR_BACNET_RPC_URL", "http://gw:9999/")
    monkeypatch.setenv("SUPERVISOR_BACNET_RPC_ENTRYPOINT", "rpc")
    monkeypatch.setenv("BACNET_RPC_API_KEY", "secret")
    cfg = load_rpc_config_from_env()
    assert cfg.base_url == "http://gw:9999"
    assert cfg.entrypoint == "/rpc"
    assert cfg.bearer_token == "secret"


@pytest.mark.asyncio
async def test_rpc_docked_create_application_uses_injected_config(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    class FakeClient:
        def __init__(self, base_url: str, timeout_s: float = 15.0, entrypoint: str = "/api", *, bearer_token=None):
            captured["base_url"] = base_url
            captured["entrypoint"] = entrypoint
            captured["bearer_token"] = bearer_token

        async def close(self) -> None:
            pass

        async def read(self, *a, **k):
            return None

        async def write(self, *a, **k):
            return None

        async def rpm(self, *a, **k):
            return []

    monkeypatch.setattr("easy_aso.runtime.rpc_docked.JsonRpcBacnetClient", FakeClient)
    cfg = BacnetRpcConfig(base_url="http://x", entrypoint="/api", bearer_token="t")
    bot = _StubRpcDocked(args=_no_server_args(), rpc_config=cfg)
    await bot.create_application()
    assert captured["base_url"] == "http://x"
    assert captured["bearer_token"] == "t"
    assert bot.app is None
    await bot.close_rpc_dock()


@pytest.mark.asyncio
async def test_rpc_docked_bacnet_read_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_client = MagicMock()
    mock_client.read = AsyncMock(return_value=42.0)
    mock_client.close = AsyncMock()

    monkeypatch.setattr("easy_aso.runtime.rpc_docked.JsonRpcBacnetClient", lambda *a, **k: mock_client)
    bot = _StubRpcDocked(args=_no_server_args(), rpc_config=BacnetRpcConfig("http://h", "/api"))
    await bot.create_application()
    val = await bot.bacnet_read("123", "analogValue,1")
    assert val == 42.0
    mock_client.read.assert_awaited_once()
    await bot.close_rpc_dock()


@pytest.mark.asyncio
async def test_rpc_docked_bacnet_rpm_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    from bacpypes3.pdu import Address

    mock_client = MagicMock()
    mock_client.rpm = AsyncMock(return_value=[{"ok": True}])
    mock_client.close = AsyncMock()
    monkeypatch.setattr("easy_aso.runtime.rpc_docked.JsonRpcBacnetClient", lambda *a, **k: mock_client)
    bot = _StubRpcDocked(args=_no_server_args(), rpc_config=BacnetRpcConfig("http://h", "/api"))
    await bot.create_application()
    addr = Address("123")
    out = await bot.bacnet_rpm(addr, "analogValue,1", "present-value")
    assert out == [{"ok": True}]
    mock_client.rpm.assert_awaited_once()
    await bot.close_rpc_dock()


@pytest.mark.asyncio
async def test_quick_agent_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    """One on_step then stop (no full ``EasyASO.run()`` signal wiring)."""

    class Quick(RpcDockedEasyASO):
        async def on_start(self) -> None:
            pass

        async def on_step(self) -> None:
            self.stop_event.set()

        async def on_stop(self) -> None:
            await self.close_rpc_dock()

    mock_client = MagicMock(close=AsyncMock(), read=AsyncMock(return_value=None))
    monkeypatch.setattr("easy_aso.runtime.rpc_docked.JsonRpcBacnetClient", lambda *a, **k: mock_client)
    bot = Quick(args=_no_server_args(), rpc_config=BacnetRpcConfig("http://h", "/api"))
    await bot.create_application()
    await bot.run_lifecycle()
    await bot.close_rpc_dock()


def test_cli_run_invokes_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict = {}

    def fake_run_agent_class(module=None, class_name=None, **kw):
        called["module"] = module
        called["class_name"] = class_name

    monkeypatch.setattr("easy_aso.runtime.runner.run_agent_class", fake_run_agent_class)
    from easy_aso.cli import agent_main

    agent_main.main(["run", "--module", "mymod", "--class", "MyCls"])
    assert called == {"module": "mymod", "class_name": "MyCls"}


def test_cli_run_help() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "easy_aso.cli.agent_main", "run", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert "--module" in proc.stdout
