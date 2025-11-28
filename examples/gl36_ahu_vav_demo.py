"""
Demonstration of a single AHU with multiple VAV boxes using the
Guideline 36 Trim & Respond algorithm.

This script creates an in‑memory BACnet network comprising one air
handling unit (AHU) and several variable air volume (VAV) terminals.
Each VAV box reports its current temperature, cooling setpoint,
control loop output, airflow and damper command.  The
``GL36TrimRespondAgent`` periodically reads these values, aggregates
cooling and static pressure requests across the zones and updates the
AHU static pressure setpoint accordingly.

Unlike the FastAPI example, this program runs a closed loop entirely
in memory; no external BACnet stack is required.  It is intended to
illustrate how the ``easy_aso`` framework can be used to implement
advanced control sequences such as ASHRAE Guideline 36 on the edge or
in a serverless function.  Because the agent logic is stateless, the
same functions could be reused in AWS Lambda or other cloud services.

To run the demo:

    python examples/gl36_ahu_vav_demo.py

You should see the static pressure setpoint adjust over a few cycles
based on the simulated zone conditions.
"""

import asyncio
from typing import List

from easy_aso.bacnet_client import InMemoryBACnetClient
from easy_aso.gl36.trim_respond import GL36TrimRespondAgent


async def setup_demo_network(bacnet: InMemoryBACnetClient, zones: List[str], ahu: str) -> None:
    """Populate the in‑memory BACnet client with initial objects.

    Parameters
    ----------
    bacnet: InMemoryBACnetClient
        The BACnet client to populate.
    zones: List[str]
        A list of zone device addresses (e.g. ``["vav1", "vav2"]``).
    ahu: str
        The address of the AHU device.

    Notes
    -----
    Each VAV has the following points:

    * ``zone_temp`` – measured zone temperature (°C)
    * ``zone_sp`` – cooling setpoint (°C)
    * ``zone_loop`` – cooling loop output (% 0–100)
    * ``zone_flow`` – measured airflow (arbitrary units)
    * ``zone_flow_sp`` – airflow setpoint (same units)
    * ``zone_damper`` – damper command (% 0–100)

    The AHU has a single point ``sp_static`` representing the static
    pressure setpoint.  The initial setpoint is 1.5 inches w.c.
    """
    # Initialise zone properties
    for zone in zones:
        await bacnet.write_property(zone, "zone_temp", 23.0)
        await bacnet.write_property(zone, "zone_sp", 22.0)
        await bacnet.write_property(zone, "zone_loop", 50.0)
        await bacnet.write_property(zone, "zone_flow", 1.0)
        await bacnet.write_property(zone, "zone_flow_sp", 1.0)
        await bacnet.write_property(zone, "zone_damper", 50.0)
    # Set initial static pressure setpoint on the AHU
    await bacnet.write_property(ahu, "sp_static", 1.5)


async def run_demo() -> None:
    """Run a short GL36 trim/respond demonstration.

    The demo runs for five cycles.  On each cycle the zone
    conditions are modified to provoke different numbers of
    cooling/pressure requests.  The agent updates the static
    pressure setpoint based on the aggregated requests and writes the
    new value back to the AHU.
    """
    bacnet = InMemoryBACnetClient()
    zones = ["vav1", "vav2", "vav3"]
    ahu = "ahu1"
    await setup_demo_network(bacnet, zones, ahu)

    # Create a GL36 trim/respond agent.  The update interval is
    # irrelevant because we manually invoke on_update() in this demo.
    agent = GL36TrimRespondAgent(
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
    )

    # Start the agent (initialises its internal state)
    await agent.on_start()

    print("Running GL36 Trim & Respond demo...\n")

    # Define some simple scenarios to drive requests
    scenarios = [
        {
            # Step 1: high temperature and high loop on vav1,
            # causing multiple cooling requests
            "vav1": {"zone_temp": 26.0, "zone_loop": 95.0},
            "vav3": {"zone_damper": 98.0, "zone_flow": 0.4},
        },
        {
            # Step 2: moderate temps but low airflow on vav2
            "vav2": {"zone_damper": 97.0, "zone_flow": 0.5},
            "vav3": {"zone_temp": 25.0, "zone_loop": 90.0},
        },
        {
            # Step 3: back to normal temps, low requests
            "vav1": {"zone_temp": 23.0, "zone_loop": 40.0},
            "vav2": {"zone_damper": 50.0, "zone_flow": 1.0},
            "vav3": {"zone_damper": 50.0, "zone_flow": 1.0},
        },
        {
            # Step 4: high damper and low flow on all zones
            "vav1": {"zone_damper": 96.0, "zone_flow": 0.6},
            "vav2": {"zone_damper": 97.0, "zone_flow": 0.4},
            "vav3": {"zone_damper": 98.0, "zone_flow": 0.3},
        },
        {
            # Step 5: stable conditions
            "vav1": {"zone_temp": 22.5},
            "vav2": {"zone_temp": 22.0},
            "vav3": {"zone_temp": 22.0},
        },
    ]

    for idx, updates in enumerate(scenarios, start=1):
        # Apply zone updates for this step
        for zone, props in updates.items():
            for obj, value in props.items():
                await bacnet.write_property(zone, obj, value)
        # Trigger one update cycle of the agent
        await agent.on_update()
        # Read back and print the new static pressure setpoint
        sp_value = await bacnet.read_property(ahu, "sp_static")
        print(f"Cycle {idx}: static pressure setpoint = {sp_value:.2f}")

    # Clean up the agent
    await agent.on_stop()


if __name__ == "__main__":
    asyncio.run(run_demo())