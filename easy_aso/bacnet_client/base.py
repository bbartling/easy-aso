from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BacnetClient(ABC):
    """Abstract BACnet client interface.

    Agents should depend on this interface rather than directly owning a BACnet/IP socket.
    """

    @abstractmethod
    async def read(
        self,
        address: str,
        object_identifier: str,
        property_identifier: str = "present-value",
    ) -> Any:
        """Read a BACnet property and return the decoded value."""
        raise NotImplementedError

    @abstractmethod
    async def write(
        self,
        address: str,
        object_identifier: str,
        value: Any,
        priority: Optional[int] = None,
        property_identifier: str = "present-value",
    ) -> None:
        """Write a BACnet property."""
        raise NotImplementedError

    @abstractmethod
    async def rpm(self, address: str, *args: str) -> List[Dict[str, Any]]:
        """ReadPropertyMultiple convenience wrapper."""
        raise NotImplementedError
