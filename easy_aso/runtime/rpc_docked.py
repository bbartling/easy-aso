"""
``EasyASO`` base class that uses :class:`~easy_aso.bacnet_client.jsonrpc_client.JsonRpcBacnetClient`
instead of a local BACnet ``Application`` (no UDP ``47808`` bind in this process).

Use this for **sidecar** or **multi-container** agents that share one BACnet gateway
(e.g. diy-bacnet-server) over JSON-RPC.

``JsonRpcBacnetClient`` expects ``address`` to be a **device instance** string for
diy-bacnet-server RPC (see that client's docstring).
"""

from __future__ import annotations

from typing import Any, List, Optional

from bacpypes3.pdu import Address

from easy_aso.bacnet_client.jsonrpc_client import JsonRpcBacnetClient
from easy_aso.easy_aso import EasyASO

from .env import BacnetRpcConfig, load_rpc_config_from_env


class RpcDockedEasyASO(EasyASO):
    """
    Subclass ``RpcDockedEasyASO``, implement ``on_start`` / ``on_step`` / ``on_stop``,
    and call ``await self.close_rpc_dock()`` from ``on_stop`` after your own teardown
    (idempotent).
    """

    def __init__(self, args=None, *, rpc_config: Optional[BacnetRpcConfig] = None) -> None:
        super().__init__(args=args)
        self._rpc_config = rpc_config

    async def create_application(self) -> None:
        prev = getattr(self, "_rpc", None)
        if prev is not None:
            try:
                await prev.close()
            except Exception:
                pass
            self._rpc = None

        cfg = self._rpc_config or load_rpc_config_from_env()
        self._rpc = JsonRpcBacnetClient(
            cfg.base_url,
            timeout_s=cfg.timeout_s,
            entrypoint=cfg.entrypoint,
            bearer_token=cfg.bearer_token,
        )
        self.app = None
        print("INFO: RpcDockedEasyASO JSON-RPC client ready (no local BACnet Application).")

    async def close_rpc_dock(self) -> None:
        rpc = getattr(self, "_rpc", None)
        if rpc is not None:
            await rpc.close()
            self._rpc = None

    async def bacnet_read(
        self,
        address: str,
        object_identifier: str,
        property_identifier: str = "present-value",
    ):
        try:
            return await self._rpc.read(address, object_identifier, property_identifier)
        except Exception as e:
            print(
                f"ERROR: RPC read failed: {e} — address={address!r} object={object_identifier!r} prop={property_identifier!r}"
            )
            return None

    async def bacnet_write(
        self,
        address: str,
        object_identifier: str,
        value: Any,
        priority: int = -1,
        property_identifier: str = "present-value",
    ):
        try:
            pri = None if priority is None or int(priority) < 0 else int(priority)
            await self._rpc.write(
                address,
                object_identifier,
                value,
                priority=pri,
                property_identifier=property_identifier,
            )
        except Exception as e:
            print(f"ERROR: RPC write failed: {e} — address={address!r} object={object_identifier!r}")

    async def bacnet_rpm(self, address: Address, *args: str):
        """
        Delegate to ``JsonRpcBacnetClient.rpm`` using ``str(address)`` as the device key.
        """
        try:
            addr = str(address)
            result: List[dict[str, Any]] = await self._rpc.rpm(addr, *args)
            return result
        except Exception as e:
            print(f"ERROR: RPC RPM failed: {e} — address={address!r} args={args!r}")
            return [{"error": str(e)}]
