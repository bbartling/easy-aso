"""Integration tests for BACnet read/write and kill switch handling.

These tests exercise a simple control agent against the in‑memory BACnet
client.  The goal is to replicate the functionality of the legacy
Docker‑based BACnet integration tests in an offline environment using
the refactored easy‑aso architecture.  A custom agent reads and
writes BACnet properties via the in‑memory client, honours a
binary‑value kill switch, and releases overrides when optimization
is disabled.
"""

from __future__ import annotations

import asyncio
import random
import unittest

from easy_aso.agent import Agent, AgentManager
from easy_aso.bacnet_client import InMemoryBACnetClient


class CustomBACnetAgent(Agent):
    """A simple agent that reads, writes and responds to a kill switch.

    The agent reads two analog values and a binary kill switch, writes
    a random float to one of the analog values, and releases all
    overrides when the kill switch is off.  It records log messages
    for verification.
    """

    def __init__(self, bacnet: InMemoryBACnetClient, update_interval: float = 0.2) -> None:
        super().__init__(update_interval=update_interval)
        self.bacnet = bacnet
        self.logs: list[str] = []
        # Track the previous optimization status to detect re‑enable events
        self._prev_opt_status: bool | None = None

    async def on_start(self) -> None:
        # Initialize previous status to True so that re‑enable detection works
        self._prev_opt_status = True
        self.logs.append("CustomBACnetAgent started")

    async def on_update(self) -> None:
        # Read the kill switch (binary value 1 present‑value)
        val = await self.bacnet.read_property("bacnet-server", "binary-value,1")
        # Coerce None to False so that missing values disable optimization
        opt_enabled = bool(val)
        self.logs.append(f"Optimization status is {opt_enabled}")
        # Detect transition from disabled to enabled
        if self._prev_opt_status is False and opt_enabled:
            self.logs.append("Optimization re-enabled. Resuming normal operation.")
        self._prev_opt_status = opt_enabled
        # If optimization is disabled, release overrides and skip normal control
        if not opt_enabled:
            self.logs.append("Optimization disabled, releasing all BACnet overrides.")
            await self.release_all()
            return
        # Optimization enabled: read present values and write a random float
        av1 = await self.bacnet.read_property("bacnet-server", "analog-value,1")
        self.logs.append(f"av1_pv {av1}")
        av2 = await self.bacnet.read_property("bacnet-server", "analog-value,2")
        self.logs.append(f"av2_pv {av2}")
        bv1 = await self.bacnet.read_property("bacnet-server", "binary-value,1")
        self.logs.append(f"bv1_pv {bv1}")
        # Write a random float to analog‑value 2 with priority 10
        rand_val = random.uniform(0.0, 100.0)
        await self.bacnet.write_property(
            "bacnet-server", "analog-value,2", rand_val, priority=10
        )
        self.logs.append("BACnet step completed.")

    async def on_stop(self) -> None:
        # On stop, release overrides
        self.logs.append("CustomBACnetAgent stopping")
        await self.release_all()

    async def release_all(self) -> None:
        """Release all BACnet overrides by writing 'null' at priority 10."""
        # Release analog‑value 2
        await self.bacnet.write_property(
            "bacnet-server", "analog-value,2", "null", priority=10
        )
        self.logs.append("All BACnet overrides have been released.")


async def fake_bacnet_device(bacnet: InMemoryBACnetClient) -> None:
    """Simulate a BACnet device toggling the kill switch and providing PVs."""
    # Initialize analog values and kill switch
    await bacnet.write_property("bacnet-server", "analog-value,1", 0.0, priority=-1)
    await bacnet.write_property("bacnet-server", "analog-value,2", 0.0, priority=-1)
    # Set kill switch to True (optimization enabled)
    await bacnet.write_property("bacnet-server", "binary-value,1", True, priority=-1)
    # Wait and then disable optimization
    await asyncio.sleep(0.3)
    await bacnet.write_property("bacnet-server", "binary-value,1", False, priority=-1)
    # Wait and then re‑enable optimization
    await asyncio.sleep(0.3)
    await bacnet.write_property("bacnet-server", "binary-value,1", True, priority=-1)


class TestBACnetIntegration(unittest.TestCase):
    """Integration test to verify BACnet read/write and kill switch behaviour."""

    def test_inmemory_bacnet_agent(self) -> None:
        async def run_test() -> None:
            bacnet = InMemoryBACnetClient()
            # Launch fake device
            device_task = asyncio.create_task(fake_bacnet_device(bacnet))
            # Create and run the custom agent
            agent = CustomBACnetAgent(bacnet, update_interval=0.2)
            mgr = AgentManager([agent])
            await mgr.start_all()
            # Let the agent run long enough to observe the kill switch toggling
            await asyncio.sleep(1.0)
            await mgr.stop_all()
            # Ensure the device task completes
            await device_task
            logs = "\n".join(agent.logs)
            # Verify that optimization was both enabled and disabled during the test
            self.assertIn("Optimization status is True", logs)
            self.assertIn("Optimization status is False", logs)
            # Check that re‑enable message is logged
            self.assertIn("Optimization re-enabled. Resuming normal operation.", logs)
            # Confirm that BACnet overrides were released
            self.assertIn("All BACnet overrides have been released.", logs)

        asyncio.run(run_test())
