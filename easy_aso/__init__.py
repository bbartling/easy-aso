"""
Public interface for the easy‑aso package.

This module exposes the agent base classes, BACnet client abstractions
and GL36 algorithms for consumers.  The original ``EasyASO`` class
has been superseded by the generic :class:`Agent` but remains for
backwards compatibility; it simply aliases the ``Agent`` class and
provides ``on_step`` as an alias of ``on_update``.
"""

from .agent import Agent, AgentManager
from .bacnet_client import BACnetClient, InMemoryBACnetClient
from .gl36 import (
    calculate_zone_requests,
    calculate_trim_respond,
    GL36TrimRespondAgent,
)


class EasyASO(Agent):  # type: ignore
    """Backwards‑compatible alias for the original EasyASO class.

    This class inherits from :class:`Agent` and defines ``on_step`` as
    an alias for ``on_update``.  Subclasses should override
    ``on_start``, ``on_step`` and ``on_stop`` as before.  The
    constructor accepts an optional ``update_interval`` argument.
    """

    def __init__(self, update_interval: float = 60.0, *args, **kwargs) -> None:
        super().__init__(update_interval=update_interval)

    async def on_step(self) -> None:
        """Alias for :meth:`Agent.on_update`.  Override in subclasses."""
        raise NotImplementedError

    # Point on_update to on_step for backwards compatibility
    async def on_update(self) -> None:
        await self.on_step()

    # Provide a no‑op __init__ signature to satisfy argparse in legacy tests
    no_bacnet_server: bool = False


__all__ = [
    "Agent",
    "AgentManager",
    "BACnetClient",
    "InMemoryBACnetClient",
    "calculate_zone_requests",
    "calculate_trim_respond",
    "GL36TrimRespondAgent",
    "EasyASO",
]
