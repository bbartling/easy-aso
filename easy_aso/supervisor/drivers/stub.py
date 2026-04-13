from __future__ import annotations

from typing import ClassVar, Sequence

from easy_aso.supervisor.store.models import Device, Point

from .base import BaseDriver, ReadBatchResult


class StubDriver(BaseDriver):
    """Deterministic driver for tests and empty BACnet installs."""

    DRIVER_TYPE: ClassVar[str] = "stub"

    async def close(self) -> None:
        return None

    async def read_points(self, device: Device, points: Sequence[Point]) -> ReadBatchResult:
        res = ReadBatchResult()
        for p in points:
            res.values[p.id] = {"stub": True, "object_identifier": p.object_identifier, "device": device.name}
        return res
