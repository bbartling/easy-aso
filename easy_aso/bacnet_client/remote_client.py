from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from .base import BacnetClient


class RemoteBacnetClient(BacnetClient):
    """BACnet client that talks to a shared bacnet-gateway over HTTP."""

    def __init__(self, base_url: str, timeout_s: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout_s)

    async def close(self) -> None:
        await self._client.aclose()

    async def read(
        self,
        address: str,
        object_identifier: str,
        property_identifier: str = "present-value",
    ) -> Any:
        r = await self._client.post(
            f"{self.base_url}/read",
            json={
                "address": address,
                "object_identifier": object_identifier,
                "property_identifier": property_identifier,
            },
        )
        r.raise_for_status()
        return r.json().get("value")

    async def write(
        self,
        address: str,
        object_identifier: str,
        value: Any,
        priority: Optional[int] = None,
        property_identifier: str = "present-value",
    ) -> None:
        r = await self._client.post(
            f"{self.base_url}/write",
            json={
                "address": address,
                "object_identifier": object_identifier,
                "property_identifier": property_identifier,
                "value": value,
                "priority": priority,
            },
        )
        r.raise_for_status()

    async def rpm(self, address: str, *args: str) -> List[Dict[str, Any]]:
        r = await self._client.post(
            f"{self.base_url}/rpm",
            json={
                "address": address,
                "args": list(args),
            },
        )
        r.raise_for_status()
        return r.json().get("results", [])
