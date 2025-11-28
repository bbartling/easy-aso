"""
BACnet client abstraction for easy‑aso.

To facilitate unit testing and decouple the control agents from a
concrete BACnet implementation, this module defines a lightweight
``BACnetClient`` class with asynchronous ``read_property``,
``write_property`` and ``read_property_multiple`` methods.  A
simple in‑memory stub is provided for use in tests and examples.

In a real deployment this interface could wrap `bacpypes3` or
another BACnet stack.  Agents consume a BACnet client instance via
dependency injection rather than importing `bacpypes3` directly.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Tuple


class BACnetClient:
    """Base class for BACnet clients.

    Concrete subclasses should override the asynchronous methods to
    perform network I/O.  The default implementation raises
    ``NotImplementedError``.
    """

    async def read_property(self, address: str, object_id: str, property_id: str = "present-value") -> Any:
        raise NotImplementedError

    async def write_property(
        self,
        address: str,
        object_id: str,
        value: Any,
        priority: int = -1,
        property_id: str = "present-value",
    ) -> Any:
        raise NotImplementedError

    async def read_property_multiple(self, address: str, parameters: List[Any]) -> List[Tuple]:
        raise NotImplementedError


class InMemoryBACnetClient(BACnetClient):
    """In‑memory BACnet client for tests and offline simulations.

    This stub stores values in an internal dictionary keyed by
    ``(address, object_id, property_id, priority)``.  Reads return the
    current value; writes update the stored value.  Priority is stored
    but not interpreted.
    """

    def __init__(self) -> None:
        # Map of (address, object, property_id, priority) -> value
        self._store: Dict[Tuple[str, str, str, int], Any] = {}

    async def read_property(self, address: str, object_id: str, property_id: str = "present-value") -> Any:
        # Return the highest priority value for the given address and object
        keys = [k for k in self._store if k[0] == address and k[1] == object_id and k[2] == property_id]
        if not keys:
            return None
        # Choose the highest priority (lowest integer) key
        key = sorted(keys, key=lambda k: k[3])[0]
        return self._store[key]

    async def write_property(
        self,
        address: str,
        object_id: str,
        value: Any,
        priority: int = -1,
        property_id: str = "present-value",
    ) -> Any:
        self._store[(address, object_id, property_id, priority)] = value
        return None

    async def read_property_multiple(self, address: str, parameters: List[Any]) -> List[Tuple]:
        # Not implemented in the stub; return empty list
        return []