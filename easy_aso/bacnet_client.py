"""
BACnet client abstraction for easy‑aso.

This module exposes a ``BACnetClient`` class that defines the
asynchronous interface used by easy‑aso agents to read and write BACnet
properties.  The default implementation stores values in memory, keyed
by ``(address, object_id, property_id, priority)``.  Reads return the
value written at the highest priority (lowest numerical value); writes
update the store.  Passing the special value ``"null"`` to
``write_property`` releases a stored override by removing it from the
store.

In a real deployment this class can be subclassed to wrap a concrete
BACnet stack such as `bacpypes3`.  The in‑memory implementation
suffices for unit tests and offline simulations.  For backwards
compatibility, an alias ``InMemoryBACnetClient`` is provided that
references ``BACnetClient``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


from typing import Any, Dict, List, Tuple


class BACnetClient:
    """
    Generic BACnet client interface used by easy‑aso agents.

    The default implementation provided here operates entirely in memory to
    facilitate unit testing and offline simulations.  Values are stored in
    an internal dictionary keyed by ``(address, object_id, property_id,
    priority)``.  Reads return the stored value with the highest priority
    (lowest numerical value), and writes update the store.  Priority is
    recorded but otherwise not interpreted.

    Concrete subclasses can override these methods to perform real BACnet
    network I/O using libraries such as `bacpypes3`.  This class is
    intentionally light‑weight and requires no external dependencies.
    """

    def __init__(self) -> None:
        # Map of (address, object_id, property_id, priority) -> value
        # Lower numerical priority values have higher precedence in BACnet.
        self._store: Dict[Tuple[str, str, str, int], Any] = {}

    async def read_property(
        self,
        address: str,
        object_id: str,
        property_id: str = "present-value",
    ) -> Any:
        """Asynchronously read a property from the in‑memory store.

        Parameters
        ----------
        address: str
            A human‑readable identifier for the remote BACnet device.  In the
            in‑memory implementation this is simply a grouping key.
        object_id: str
            The BACnet object identifier (e.g. ``"analog-value,1"``).
        property_id: str
            The BACnet property identifier (default ``"present-value"``).

        Returns
        -------
        Any or None
            The value stored at the highest priority, or ``None`` if no
            matching entry exists.
        """
        # Filter keys matching the requested address, object and property
        keys = [k for k in self._store if k[0] == address and k[1] == object_id and k[2] == property_id]
        if not keys:
            return None
        # Select the value with the highest priority (lowest integer priority)
        key = sorted(keys, key=lambda k: k[3])[0]
        return self._store[key]

    async def write_property(
        self,
        address: str,
        object_id: str,
        value: Any,
        priority: int = -1,
        property_id: str = "present-value",
    ) -> None:
        """Asynchronously write a property into the in‑memory store.

        Parameters
        ----------
        address: str
            A human‑readable identifier for the remote BACnet device.
        object_id: str
            The BACnet object identifier (e.g. ``"analog-value,1"``).
        value: Any
            The value to store.  A value of ``"null"`` signifies a BACnet
            release and will remove all stored overrides for the given
            ``address``/``object_id``/``property_id`` at the specified
            priority.
        priority: int
            The BACnet write priority.  Lower numerical values indicate
            higher precedence.  Defaults to ``-1`` to simulate the BACnet
            default priority.  The priority value is used as part of the
            storage key but is not otherwise interpreted.
        property_id: str
            The BACnet property identifier (default ``"present-value"``).
        """
        # If the caller passes "null" then this represents a BACnet release.
        # Remove the matching entry instead of storing a literal string.
        if value == "null":
            # Remove all entries matching this address/object/property/priority
            keys_to_remove = [
                k
                for k in list(self._store.keys())
                if k[0] == address and k[1] == object_id and k[2] == property_id and k[3] == priority
            ]
            for k in keys_to_remove:
                del self._store[k]
            return None
        # Otherwise store the value along with the priority
        self._store[(address, object_id, property_id, priority)] = value
        return None

    async def read_property_multiple(self, address: str, parameters: List[Any]) -> List[Tuple]:
        """Asynchronously read multiple properties.

        This simple in‑memory implementation does not support ReadPropertyMultiple
        semantics and returns an empty list.  Subclasses integrating with
        real BACnet stacks should override this method to return a list of
        tuples ``(object_identifier, property_identifier, property_array_index, value)``.

        Parameters
        ----------
        address: str
            Device address to query.
        parameters: list
            A list of object identifiers and property reference lists as defined
            by the BACnet ReadPropertyMultiple service.

        Returns
        -------
        List[Tuple]
            An empty list in the in‑memory implementation.
        """
        return []


# Maintain backwards compatibility for existing code that imports
# ``InMemoryBACnetClient`` from this module.  The alias points to
# ``BACnetClient`` which now provides the in‑memory implementation.  This
# preserves the public API while discouraging direct use of the class name.
InMemoryBACnetClient = BACnetClient