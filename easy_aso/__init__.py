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

# Import the legacy EasyASO implementation using bacpypes3
from .easy_aso import EasyASO

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
