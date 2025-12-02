"""
Multi‑agent demonstration using the easy‑aso agent framework.

This script illustrates how multiple control agents can be run
concurrently in a single process.  Two agents are defined:

* ``GL36TrimRespondAgent`` – implements ASHRAE Guideline 36 trim & respond
  logic for resetting the static pressure setpoint of an air handling
  unit (AHU) based on requests from multiple VAV boxes.
* ``BuildingSupervisorAgent`` – a simple supervisory control agent that
  adjusts VAV heating setpoints based on a simulated occupancy schedule.

Both agents share an ``InMemoryBACnetClient`` so they can read and
write BACnet points without talking to external devices.  An
``AgentManager`` starts the agents and runs their update loops
concurrently.  A demonstration loop runs for a few cycles, printing
the AHU static pressure setpoint and one of the VAV heating setpoints
to show the agents working together.

To run this demo, install ``easy_aso`` and execute:

    python multi_agent_demo.py

This will run the agents for five cycles and then stop them.
"""

import asyncio
from dataclasses import dataclass
from typing import Iterable, List

from easy_aso.agent import Agent, AgentManager
from easy_aso.bacnet_client import InMemoryBACnetClient
from easy_aso.gl36.trim_respond import GL36TrimRespondAgent


@dataclass
class BuildingSupervisorAgent(Agent):
    """Simple supervisor that toggles heating setpoints based on occupancy.

    For demonstration purposes this agent alternates between occupied
    and unoccupied every update cycle.  When occupied it writes a
    higher heating setpoint to each VAV box; when unoccupied it writes
    a lower setpoint.  In a real implementation the occupancy state
    would come from a schedule or sensor.
    """

    bacnet: InMemoryBACnetClient
    zone_addresses: Iterable[str]
    heat_setpoint_occ: float
    heat_setpoint_unocc: float
    sp_object: str = "heat_sp"
    update_interval: float = 5.0

    # Internal state not set via constructor
    _occupied: bool = False

    async def on_start(self) -> None:
        # Initialise all zones to the unoccupied setpoint
        for addr in self.zone_addresses:
            await self.bacnet.write_property(addr, self.sp_object, self.heat_setpoint_unocc)

    async def on_update(self) -> None:
        # Toggle occupancy state each update for demonstration
        self._occupied = not self._occupied
        setpoint = self.heat_setpoint_occ if self._occupied else self.heat_setpoint_unocc
        for addr in self.zone_addresses:
            await self.bacnet.write_property(addr, self.sp_object, setpoint)

    async def on_stop(self) -> None:
        # Nothing to clean up
        pass


async def main() -> None:
    """Entry point for running the multi‑agent demonstration."""
    bacnet = InMemoryBACnetClient()

    # Define devices
    zones: List[str] = ["vav1", "vav2", "vav3"]
    ahu = "ahu1"

    # Populate initial BACnet points
    # VAV points used by the GL36 agent
    for zone in zones:
        await bacnet.write_property(zone, "zone_temp", 23.0)
        await bacnet.write_property(zone, "zone_sp", 22.0)
        await bacnet.write_property(zone, "zone_loop", 50.0)
        await bacnet.write_property(zone, "zone_flow", 1.0)
        await bacnet.write_property(zone, "zone_flow_sp", 1.0)
        await bacnet.write_property(zone, "zone_damper", 50.0)
    # AHU static pressure setpoint
    await bacnet.write_property(ahu, "sp_static", 1.5)

    # Create a GL36 trim/respond agent
    trim_agent = GL36TrimRespondAgent(
        bacnet=bacnet,
        zone_addresses=zones,
        zone_temp_obj="zone_temp",
        zone_sp_obj="zone_sp",
        zone_loop_obj="zone_loop",
        zone_flow_obj="zone_flow",
        zone_flow_sp_obj="zone_flow_sp",
        zone_damper_obj="zone_damper",
        sp_address=ahu,
        sp_object="sp_static",
        sp_min=1.0,
        sp_max=3.0,
        sp_trim=0.1,
        sp_res=-0.05,
        sp_res_max=0.1,
        ignored_requests=0,
        use_imperial=False,
        update_interval=2.0,
    )

    # Create a building supervisor agent
    supervisor_agent = BuildingSupervisorAgent(
        bacnet=bacnet,
        zone_addresses=zones,
        heat_setpoint_occ=72.0,
        heat_setpoint_unocc=60.0,
        update_interval=3.0,
    )

    # Start both agents via the manager
    manager = AgentManager([trim_agent, supervisor_agent])
    await manager.start_all()

    print("Running multi‑agent demo...\n")

    # Demonstration loop: change some zone conditions and print results
    scenarios = [
        {
            "vav1": {"zone_temp": 26.0, "zone_loop": 95.0},
            "vav3": {"zone_damper": 98.0, "zone_flow": 0.4},
        },
        {
            "vav2": {"zone_damper": 97.0, "zone_flow": 0.5},
            "vav3": {"zone_temp": 25.0, "zone_loop": 90.0},
        },
        {
            "vav1": {"zone_temp": 23.0, "zone_loop": 40.0},
            "vav2": {"zone_damper": 50.0, "zone_flow": 1.0},
            "vav3": {"zone_damper": 50.0, "zone_flow": 1.0},
        },
    ]

    for idx, updates in enumerate(scenarios, start=1):
        # Apply zone updates for this step
        for zone, props in updates.items():
            for obj, value in props.items():
                await bacnet.write_property(zone, obj, value)
        # Wait a short time to allow agents to run their update loops
        await asyncio.sleep(2.5)
        # Print current AHU SP and one VAV heating SP
        sp = await bacnet.read_property(ahu, "sp_static")
        heat_sp = await bacnet.read_property(zones[0], "heat_sp")
        print(f"Cycle {idx}: AHU static pressure SP = {sp:.2f}, VAV1 heat SP = {heat_sp}")

    # Stop all agents
    await manager.stop_all()

    print("\nDemo complete. Agents stopped.")


if __name__ == "__main__":
    asyncio.run(main())