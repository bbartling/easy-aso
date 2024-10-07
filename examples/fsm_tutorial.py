import time
import random
import asyncio
from datetime import datetime, timedelta
from enum import Enum

class HVACState(Enum):
    IDLE = "idle"
    BUILDING_STARTUP = "building_startup"
    BUILDING_SHUTDOWN = "building_shutdown"
    MONITORING_OCCUPIED = "monitoring_occupied"
    MONITORING_UNOCCUPIED = "monitoring_unoccupied"
    OPTIMIZING_OCC = "optimizing_occupied"
    OPTIMIZING_UNOCC = "optimizing_unoccupied"
    COMMISSIONING = "commissioning"  # Special commissioning state

# Generic State Machine for any ASO strategy
class EasyASO:
    async def bacnet_read(self, addr, obj_id):
        # Simulate BACnet read
        return random.uniform(60.0, 85.0)  # Example temperature reading

    async def bacnet_write(self, addr, obj_id, value):
        # Simulate BACnet write
        print(f"BACnet write to {addr} {obj_id}: {value}")

    async def on_start(self):
        pass

    async def on_step(self):
        pass

    async def on_stop(self):
        pass

class CustomHvacBot(EasyASO):
    def __init__(self, telemetry, commissioning_duration=20):
        self.telemetry = telemetry
        self.state = HVACState.IDLE
        self.commissioning_duration = commissioning_duration  # in minutes
        self.commissioning_start_time = None
        self.ahu_state = {
            'oa_damper': 0,  # Outdoor Air Damper position
            'cooling_valve': 0,  # Cooling Valve position
            'heating_valve': 0,  # Heating Valve position
            'mix_temp': None,
            'supply_temp': None,
            'return_temp': None
        }

    async def on_start(self):
        # Custom start logic - BACnet read request
        print(f"System starting in state: {self.state.value}")

    async def transition_to(self, new_state):
        print(f"Transitioning from {self.state.value} to {new_state.value}")
        self.state = new_state

    async def handle_state(self):
        """Run logic based on the current state."""
        current_time = datetime.now().strftime("%H:%M:%S")
        print(f"[{current_time}] Currently in state: {self.state.value}")

        if self.state == HVACState.IDLE:
            print("System is idle, waiting for next scheduled action.")
            # Move to commissioning if it's time
            if self.check_commissioning_time():
                await self.transition_to(HVACState.COMMISSIONING)

        elif self.state == HVACState.COMMISSIONING:
            print("Running self-commissioning AHU system.")
            await self.run_commissioning_cycle()

        # Other states (start-up, shutdown, monitoring) can be added similarly.

    def check_commissioning_time(self):
        """Checks if it's time to start the commissioning cycle."""
        current_time = datetime.now()
        # Example: Start commissioning cycle at noon (12:00 PM)
        commissioning_start_time = current_time.replace(hour=12, minute=0, second=0, microsecond=0)
        return current_time >= commissioning_start_time

    async def run_commissioning_cycle(self):
        """Runs the self-commissioning process."""
        print("Starting AHU commissioning cycle...")

        # Close outdoor air dampers and set valves to off
        await self.bacnet_write("ahu1", "oa_damper", 0)  # Close dampers
        await self.bacnet_write("ahu1", "cooling_valve", 0)  # Turn off cooling
        await self.bacnet_write("ahu1", "heating_valve", 0)  # Turn off heating

        self.commissioning_start_time = datetime.now()

        # Wait for commissioning cycle to complete (20 minutes in this case)
        await asyncio.sleep(self.commissioning_duration * 60)  # Simulating the time duration

        # Collect temperature readings
        self.ahu_state['mix_temp'] = await self.bacnet_read("ahu1", "mix_temp")
        self.ahu_state['supply_temp'] = await self.bacnet_read("ahu1", "supply_temp")
        self.ahu_state['return_temp'] = await self.bacnet_read("ahu1", "return_temp")

        # Run fault detection logic
        await self.run_fault_detection()

        # Return system to idle after commissioning
        await self.transition_to(HVACState.IDLE)

    async def run_fault_detection(self):
        """Runs a fault detection check on the AHU temperature sensors."""
        print("Running fault detection...")

        mix_temp = self.ahu_state['mix_temp']
        supply_temp = self.ahu_state['supply_temp']
        return_temp = self.ahu_state['return_temp']

        # Define acceptable temp difference (+/- 2F for fan heat)
        acceptable_diff = 2.0
        if abs(mix_temp - return_temp) > acceptable_diff or abs(mix_temp - supply_temp) > acceptable_diff:
            print(f"Fault detected! Temperature mismatch: mix: {mix_temp}, return: {return_temp}, supply: {supply_temp}")
        else:
            print("No faults detected. Temperature sensors are within acceptable range.")

    async def on_stop(self):
        # Custom stop logic - BACnet release request
        await self.bacnet_write("ahu1", "oa_damper", "null")  # Release damper
        await self.bacnet_write("ahu1", "cooling_valve", "null")  # Release cooling valve
        await self.bacnet_write("ahu1", "heating_valve", "null")  # Release heating valve
        print("System stopped and released to normal operation.")


# Simulate FSM cycle
async def simulate_fsm():
    telemetry = {"occupancy": False}  # Example telemetry data
    bot = CustomHvacBot(telemetry)

    await bot.on_start()

    # Run for a few cycles
    for step in range(5):
        await bot.handle_state()
        await asyncio.sleep(10)  # Simulating time between steps

    await bot.on_stop()

# Run the simulation
asyncio.run(simulate_fsm())
