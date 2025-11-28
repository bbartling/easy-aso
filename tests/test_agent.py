"""
Unit tests for the easy_aso agent framework and Guideline 36 logic.

These tests exercise the asynchronous agent lifecycle, the stub BACnet
client, and the Trim & Respond functions used to implement ASHRAE
Guideline 36 reset loops.  The intent is to validate that the
refactored architecture inspired by VOLTTRON behaves as expected
without requiring external BACnet servers or Docker containers.
"""

from __future__ import annotations

import asyncio
import unittest

from easy_aso.agent import Agent, AgentManager
from easy_aso.bacnet_client import InMemoryBACnetClient
from easy_aso.gl36 import (
    calculate_zone_requests,
    calculate_trim_respond,
    GL36TrimRespondAgent,
)
from easy_aso import EasyASO


class TestAgentLifecycle(unittest.TestCase):
    """Verify that the Agent base class schedules lifecycle hooks."""

    def test_agent_is_abstract(self) -> None:
        # Agent should remain an abstract class
        with self.assertRaises(TypeError):  # cannot instantiate directly
            Agent()  # type: ignore

    def test_agent_manager_runs_agent(self) -> None:
        events: list[str] = []

        class SampleAgent(Agent):
            async def on_start(self) -> None:
                events.append("start")

            async def on_update(self) -> None:
                events.append("update")
                # stop after first update to avoid infinite loop
                self.stop()

            async def on_stop(self) -> None:
                events.append("stop")

        async def run_agent() -> None:
            mgr = AgentManager([SampleAgent(update_interval=0.01)])
            await mgr.start_all()
            # allow one update cycle to run
            await asyncio.sleep(0.05)
            await mgr.stop_all()

        asyncio.run(run_agent())
        # Ensure that all lifecycle methods were called
        self.assertIn("start", events)
        self.assertIn("update", events)
        self.assertIn("stop", events)


class TestEasyASOCompatibility(unittest.TestCase):
    """Ensure the backwards‑compatible EasyASO alias functions correctly."""

    def test_easyaso_is_subclass_of_agent(self) -> None:
        self.assertTrue(issubclass(EasyASO, Agent))

    def test_easyaso_abstract_methods(self) -> None:
        # Attempting to instantiate EasyASO without implementing lifecycle
        # methods should raise a TypeError due to abstract methods.
        with self.assertRaises(TypeError):  # type: ignore
            EasyASO()

        # Define a minimal subclass implementing the required methods
        class MyEasyASO(EasyASO):
            async def on_start(self) -> None:
                pass

            async def on_step(self) -> None:
                pass

            async def on_stop(self) -> None:
                pass

        # Instance can be created without args
        instance = MyEasyASO(update_interval=0.1)
        self.assertIsInstance(instance, MyEasyASO)


class TestGL36Functions(unittest.TestCase):
    """Test the stateless G36 helper functions."""

    def test_calculate_zone_requests(self) -> None:
        # Temperature difference exactly at the medium threshold (2 °C) should request 2 cooling requests
        c_req, p_req = calculate_zone_requests(
            zone_temp=22.0,
            zone_setpoint=20.0,
            cooling_loop_pct=100.0,
            airflow=100.0,
            airflow_setpoint=200.0,
            damper_cmd_pct=80.0,
        )
        self.assertEqual(c_req, 2)
        # Damper at 95% and airflow less than 50% of setpoint triggers 3 pressure requests
        _, p_req = calculate_zone_requests(
            zone_temp=25.0,
            zone_setpoint=20.0,
            cooling_loop_pct=50.0,
            airflow=40.0,
            airflow_setpoint=100.0,
            damper_cmd_pct=95.0,
        )
        self.assertEqual(p_req, 3)

    def test_calculate_trim_respond(self) -> None:
        # When requests exceed the ignored threshold, the setpoint should increase by sp_trim
        new_sp = calculate_trim_respond(
            current_sp=2.0,
            sp_min=1.0,
            sp_max=3.0,
            num_requests=5,
            ignored_requests=2,
            sp_trim=0.5,
            sp_res=-0.2,
            sp_res_max=0.5,
        )
        self.assertAlmostEqual(new_sp, 2.5)
        # When requests are below the ignored threshold, the setpoint should decrease (sp_res)
        new_sp = calculate_trim_respond(
            current_sp=2.5,
            sp_min=1.0,
            sp_max=3.0,
            num_requests=0,
            ignored_requests=1,
            sp_trim=0.5,
            sp_res=-0.4,
            sp_res_max=0.2,
        )
        # Limit by sp_res_max (0.2) since sp_res magnitude (0.4) exceeds it
        self.assertAlmostEqual(new_sp, 2.3)


class TestGL36Agent(unittest.TestCase):
    """Validate the GL36TrimRespondAgent behaviour with the in‑memory BACnet client."""

    def test_trim_respond_agent(self) -> None:
        async def run_agent() -> None:
            # Prepare an in‑memory BACnet client with two zones
            bacnet = InMemoryBACnetClient()
            # Initialize zone data: zone 1 with high temp and low airflow to trigger requests
            bacnet._store.update({
                ("zone1", "temp", "present-value", -1): 25.0,
                ("zone1", "spt", "present-value", -1): 20.0,
                ("zone1", "loop", "present-value", -1): 100.0,
                ("zone1", "flow", "present-value", -1): 40.0,
                ("zone1", "flow_sp", "present-value", -1): 100.0,
                ("zone1", "damper", "present-value", -1): 95.0,
                # zone 2 with no requests
                ("zone2", "temp", "present-value", -1): 20.0,
                ("zone2", "spt", "present-value", -1): 20.0,
                ("zone2", "loop", "present-value", -1): 50.0,
                ("zone2", "flow", "present-value", -1): 100.0,
                ("zone2", "flow_sp", "present-value", -1): 100.0,
                ("zone2", "damper", "present-value", -1): 50.0,
                # initial static pressure setpoint
                ("ahu", "sp", "present-value", -1): 2.0,
            })
            # Create the agent
            agent = GL36TrimRespondAgent(
                bacnet=bacnet,
                zone_addresses=["zone1", "zone2"],
                zone_temp_obj="temp",
                zone_sp_obj="spt",
                zone_loop_obj="loop",
                zone_flow_obj="flow",
                zone_flow_sp_obj="flow_sp",
                zone_damper_obj="damper",
                sp_address="ahu",
                sp_object="sp",
                sp_min=1.0,
                sp_max=3.0,
                sp_trim=0.5,
                sp_res=-0.2,
                sp_res_max=0.5,
                ignored_requests=1,
                update_interval=0.1,
            )
            mgr = AgentManager([agent])
            await mgr.start_all()
            # Let the agent run long enough for exactly one update (on_update is called
            # immediately on start, then the next update happens after update_interval).
            await asyncio.sleep(0.05)
            await mgr.stop_all()
            # Read the written setpoint
            new_sp = await bacnet.read_property("ahu", "sp")
            # Zone1: 3 cooling + 3 pressure requests, zone2: 0 => total 6 > ignored (1)
            # So setpoint should increase by sp_trim (0.5) from initial 2.0 to 2.5
            self.assertAlmostEqual(new_sp, 2.5)

        asyncio.run(run_agent())


if __name__ == "__main__":
    unittest.main()