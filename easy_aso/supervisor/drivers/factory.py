from __future__ import annotations

from easy_aso.supervisor.store.models import Device

from .base import BaseDriver
from .stub import StubDriver


def create_driver(device: Device) -> BaseDriver:
    dt = device.driver_type.strip().lower()
    if dt == StubDriver.DRIVER_TYPE:
        return StubDriver()
    if dt == "bacnet_jsonrpc":
        from .bacnet_jsonrpc import BacnetJsonRpcDriver

        return BacnetJsonRpcDriver(device)
    raise ValueError(f"Unsupported driver_type: {device.driver_type!r}")
