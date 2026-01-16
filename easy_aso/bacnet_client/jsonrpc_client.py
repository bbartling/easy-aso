from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import httpx

from .base import BacnetClient


class JsonRpcBacnetClient(BacnetClient):
    """BACnet client that talks to diy-bacnet-server via JSON-RPC.

    IMPORTANT: diy-bacnet-server's BACnet *client* RPC methods are keyed by
    `device_instance` (int), not an IP address string. In easy-aso we keep the
    `address` parameter for API compatibility, but for this client it must be a
    device instance (e.g. "3456789").

    Default entrypoint for fastapi-jsonrpc is `/api`.
    """

    def __init__(self, base_url: str, timeout_s: float = 15.0, entrypoint: str = "/api"):
        self.base_url = base_url.rstrip("/")
        self.entrypoint = entrypoint
        self._client = httpx.AsyncClient(timeout=timeout_s)

    async def close(self) -> None:
        await self._client.aclose()

    def _device_instance(self, address: str) -> int:
        # allow a couple convenient forms
        s = str(address).strip()
        if s.lower().startswith("device:"):
            s = s.split(":", 1)[1].strip()
        return int(s)

    async def _rpc(self, method: str, params: Dict[str, Any]) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params,
        }
        r = await self._client.post(f"{self.base_url}{self.entrypoint}", json=payload)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            # normalize into a readable exception
            raise RuntimeError(f"JSON-RPC error calling {method}: {data['error']}")
        return data.get("result")

    async def read(
        self,
        address: str,
        object_identifier: str,
        property_identifier: str = "present-value",
    ) -> Any:
        device_instance = self._device_instance(address)
        result = await self._rpc(
            "client_read_property",
            {
                "request": {
                    "device_instance": device_instance,
                    "object_identifier": object_identifier,
                    "property_identifier": property_identifier,
                }
            },
        )
        # diy-bacnet-server returns {"present-value": <val>} (or property_identifier key)
        if isinstance(result, dict) and property_identifier in result:
            return result[property_identifier]
        return result

    async def write(
        self,
        address: str,
        object_identifier: str,
        value: Any,
        priority: Optional[int] = None,
        property_identifier: str = "present-value",
    ) -> None:
        device_instance = self._device_instance(address)
        await self._rpc(
            "client_write_property",
            {
                "request": {
                    "device_instance": device_instance,
                    "object_identifier": object_identifier,
                    "property_identifier": property_identifier,
                    "value": value,
                    "priority": priority,
                }
            },
        )

    async def rpm(self, address: str, *args: str) -> List[Dict[str, Any]]:
        device_instance = self._device_instance(address)

        if len(args) % 2 != 0:
            raise ValueError(
                "RPM args must be (object_identifier property_identifier) pairs, e.g. "
                "'analogValue,1 present-value analogValue,1 units'"
            )

        requests: List[Dict[str, str]] = []
        for i in range(0, len(args), 2):
            requests.append({"object_identifier": args[i], "property_identifier": args[i + 1]})

        result = await self._rpc(
            "client_read_multiple",
            {
                "request": {
                    "device_instance": device_instance,
                    "requests": requests,
                }
            },
        )

        # client_read_multiple returns BaseResponse-like: {success, message, data:{results:[...]}}
        if isinstance(result, dict):
            data = result.get("data", {})
            if isinstance(data, dict) and "results" in data:
                return data.get("results", [])
        # fallback
        return result if isinstance(result, list) else []
