from __future__ import annotations

import os
from typing import Any, ClassVar, List, Sequence, Tuple

from easy_aso.bacnet_client.jsonrpc_client import JsonRpcBacnetClient
from easy_aso.supervisor.store.models import Device, Point

from .base import BaseDriver, ReadBatchResult


def _norm_key(obj: str, prop: str) -> Tuple[str, str]:
    return (obj.strip().lower().replace(" ", ""), prop.strip().lower().replace(" ", ""))


class BacnetJsonRpcDriver(BaseDriver):
    """Poll BACnet devices through diy-bacnet-server JSON-RPC (RPM batching)."""

    DRIVER_TYPE: ClassVar[str] = "bacnet_jsonrpc"

    def __init__(self, device: Device) -> None:
        self._device = device
        base = device.rpc_base_url or os.environ.get("SUPERVISOR_BACNET_RPC_URL", "http://127.0.0.1:8080")
        entry = device.rpc_entrypoint or os.environ.get("SUPERVISOR_BACNET_RPC_ENTRYPOINT", "/api")
        self._client = JsonRpcBacnetClient(base, entrypoint=entry)

    async def close(self) -> None:
        await self._client.close()

    async def read_points(self, device: Device, points: Sequence[Point]) -> ReadBatchResult:
        if not points:
            return ReadBatchResult()
        addr = device.device_address
        rpm_args: List[str] = []
        order: List[Tuple[str, str, str]] = []
        for p in points:
            rpm_args.extend([p.object_identifier, p.property_identifier])
            order.append((p.id, p.object_identifier, p.property_identifier))

        try:
            rows = await self._client.rpm(addr, *rpm_args)
        except Exception as exc:  # noqa: BLE001
            err = str(exc)
            return ReadBatchResult(errors={pid: err for pid, _, _ in order})

        if not isinstance(rows, list):
            err = "RPM response was not a list"
            return ReadBatchResult(errors={pid: err for pid, _, _ in order})

        out = ReadBatchResult()
        if len(rows) == len(points):
            for p, item in zip(points, rows):
                if not isinstance(item, dict):
                    out.errors[p.id] = "non-dict RPM row"
                    continue
                val = item.get("value")
                if isinstance(val, str) and val.startswith("Error"):
                    out.errors[p.id] = val
                else:
                    out.values[p.id] = val
            return out

        keyed: dict[Tuple[str, str], Any] = {}
        for item in rows:
            if not isinstance(item, dict):
                continue
            oid = item.get("object_identifier")
            pid = item.get("property_identifier")
            if oid is None or pid is None:
                continue
            oid_s = str(oid)
            pid_s = str(pid)
            keyed[_norm_key(oid_s, pid_s)] = item.get("value")

        for point_id, obj, prop in order:
            key = _norm_key(obj, prop)
            if key in keyed:
                val = keyed[key]
                if isinstance(val, str) and val.startswith("Error"):
                    out.errors[point_id] = val
                else:
                    out.values[point_id] = val
            else:
                out.errors[point_id] = "missing result for object/property in RPM response"
        return out
