import asyncio
from easy_aso import EasyASO
from enum import Enum
from datetime import datetime, timedelta

"""
BuildingFSM class extends EasyASO to manage HVAC control using a finite state machine (FSM). 
It monitors building occupancy and dynamically transitions between occupied and unoccupied states, 
applying energy efficiency strategies such as duct static pressure reset and zone-based air control 
using motion detectors. The class continuously checks outside air temperature and updates relevant devices 
like the AHU for economizer logic. During unoccupied times, it maintains setpoints and controls VAV zones 
accordingly. It also periodically releases all BACnet overrides when optimization is inactive.
"""

# BACnet configuration constants
BOILER_IP = "10.200.200.233"
BOILER_OUTSIDE_AIR_SENSOR = "analog-input,1"

AHU_IP = "10.200.200.233"
AHU_OUTSIDE_AIR_VALUE = "analog-value,2"
AHU_OCCUPANCY = "multi-state-value,1"
AHU_ZONE_TEMP = "analog-value,5"
AHU_DUCT_STATIC_PRESSURE = "analog-output,7"

VAV_ADDRESSES = [
    "10.200.200.233",
    "10.200.200.233",
    "10.200.200.233",
]
MOTION_DETECTOR = "binary-input,9"
UNOCCUPIED_HEAT_SETPOINT = 60.0
OCCUPIED_HEAT_SETPOINT = 72.0
OCCUPIED_COOL_SETPOINT = 75.0
UNOCCUPIED_COOL_SETPOINT = 85.0
VAV_ZONE_SETPOINT = "analog-value,4"
VAV_ZONE_AIR_TEMP = "analog-value,8"

# Building operation schedule constants
BUILDING_STARTUP = "08:00"
BUILDING_SHUTDOWN = "18:00"

# Day occupancy configuration
OCCUPANCY_SCHEDULE = {
    0: True,  # Monday
    1: True,  # Tuesday
    2: True,  # Wednesday
    3: True,  # Thursday
    4: True,  # Friday
    5: False,  # Saturday
    6: False,  # Sunday
}


# FSM States for Supervisory Control
class HVACState(Enum):
    IDLE = "idle"
    MONITORING_OCCUPIED = "monitoring_occupied"
    MONITORING_UNOCCUPIED = "monitoring_unoccupied"
    ADJUSTING = "adjusting"
    RELEASE_OVERRIDE = "release_override"


# FSM Transitions
transitions = {
    HVACState.IDLE: [HVACState.MONITORING_OCCUPIED, HVACState.MONITORING_UNOCCUPIED],
    HVACState.MONITORING_OCCUPIED: [HVACState.ADJUSTING, HVACState.RELEASE_OVERRIDE],
    HVACState.MONITORING_UNOCCUPIED: [HVACState.ADJUSTING, HVACState.RELEASE_OVERRIDE],
    HVACState.ADJUSTING: [
        HVACState.MONITORING_OCCUPIED,
        HVACState.MONITORING_UNOCCUPIED,
    ],
    HVACState.RELEASE_OVERRIDE: [HVACState.IDLE],
}


# FSM Transition Check
def can_transition(current_state, next_state):
    return next_state in transitions.get(current_state, [])


class BuildingFSM(EasyASO):

    def __init__(self):
        super().__init__()
        self.state = HVACState.IDLE
        self.last_outside_air_update = datetime.now()
        self.last_vav_temp_update = datetime.now()
        self.last_occupancy_status = self.is_occupied()
        self.last_release_time = datetime.now()

    async def on_start(self):
        print("BuildingFSM started. Determining initial state...")
        if self.is_occupied():
            self.transition_to(HVACState.MONITORING_OCCUPIED)
        else:
            self.transition_to(HVACState.MONITORING_UNOCCUPIED)

    async def on_step(self):
        """Periodic task to manage the
        FSM states and transitions."""

        while True:
            await self.handle_state()
            await asyncio.sleep(2)

    async def handle_state(self):
        """Handle actions based on
        the current state."""

        current_time = datetime.now()

        if self.state == HVACState.MONITORING_OCCUPIED:
            await self.monitor_occupied_building()

        elif self.state == HVACState.MONITORING_UNOCCUPIED:
            await self.monitor_unoccupied_building()

        elif self.state == HVACState.ADJUSTING:
            await self.adjust_setpoints()

        elif self.state == HVACState.RELEASE_OVERRIDE:
            print("Releasing all BACnet overrides.")
            await self.release_all()
            self.transition_to(HVACState.IDLE)

    def is_occupied(self):
        """Check if the building is occupied
        based on the time and day."""

        current_time = datetime.now().time()
        current_day = datetime.now().weekday()

        if OCCUPANCY_SCHEDULE.get(current_day, False):
            occupied_start = datetime.strptime(BUILDING_STARTUP, "%H:%M").time()
            occupied_end = datetime.strptime(BUILDING_SHUTDOWN, "%H:%M").time()
            return occupied_start <= current_time <= occupied_end

        return False

    async def monitor_occupied_building(self):
        """Energy efficiency strategies
        for occupied building."""

        print("Monitoring occupied building...")
        await self.update_outside_air_temp()

        await self.static_pressure_reset()

        for address in VAV_ADDRESSES:
            motion_detected = await self.bacnet_read(address, MOTION_DETECTOR)
            if not motion_detected:
                # If no motion detected, close air to save energy
                print(
                    f"Zone at {address} is in occupied-standby. Closing air to the zone."
                )
                await self.bacnet_write(
                    address, VAV_ZONE_SETPOINT, UNOCCUPIED_HEAT_SETPOINT, 16
                )

    async def monitor_unoccupied_building(self):
        """Monitor unoccupied building
        and control temperature."""
        print("Monitoring unoccupied building...")
        await self.update_outside_air_temp()

        current_time = datetime.now()
        if (current_time - self.last_vav_temp_update).total_seconds() >= 300:
            await self.average_vav_zone_temp_and_control_ahu()
            self.last_vav_temp_update = current_time

    async def adjust_setpoints(self):
        """Adjust setpoints based on occupancy."""
        if self.is_occupied():
            self.heat_setpoint = OCCUPIED_HEAT_SETPOINT
            cool_setpoint = OCCUPIED_COOL_SETPOINT
            ahu_occupancy_value = 1  # Occupied
            print("Building occupied: Setting occupied setpoints.")
        else:
            self.heat_setpoint = UNOCCUPIED_HEAT_SETPOINT
            cool_setpoint = UNOCCUPIED_COOL_SETPOINT
            ahu_occupancy_value = 2  # Unoccupied
            print("Building unoccupied: Setting unoccupied setpoints.")

        # Apply setpoints to VAVs
        for address in VAV_ADDRESSES:
            await self.bacnet_write(address, VAV_ZONE_SETPOINT, self.heat_setpoint, 16)

        # Apply AHU occupancy status
        await self.bacnet_write(AHU_IP, AHU_OCCUPANCY, ahu_occupancy_value, 16)

    async def update_outside_air_temp(self):
        """Update outside air temperature
        globally for all devices."""
        outside_air_temp = await self.bacnet_read(BOILER_IP, BOILER_OUTSIDE_AIR_SENSOR)
        await self.bacnet_write(AHU_IP, AHU_OUTSIDE_AIR_VALUE, outside_air_temp, 16)
        print(f"Updated outside air temperature: {outside_air_temp}")

    async def average_vav_zone_temp_and_control_ahu(self):
        """Average VAV zone temperature during
        unoccupied times and control AHU."""
        temperatures = []
        for address in VAV_ADDRESSES:
            temp = await self.bacnet_read(address, VAV_ZONE_AIR_TEMP)
            temperatures.append(temp)

        if temperatures:
            average_temp = sum(temperatures) / len(temperatures)
            print(f"Average VAV zone temperature: {average_temp}")
            await self.bacnet_write(AHU_IP, AHU_ZONE_TEMP, average_temp, 16)

    async def static_pressure_reset(self):
        """TODO
        Simulate an AHU duct static
        pressure reset for energy efficiency."""

        print("Adjusting AHU duct static pressure for energy efficiency.")
        new_static_pressure = 1.0
        await self.bacnet_write(
            AHU_IP, AHU_DUCT_STATIC_PRESSURE, new_static_pressure, 16
        )

    async def release_all(self):
        """Release all BACnet overrides."""
        for address in VAV_ADDRESSES:
            await self.bacnet_write(address, VAV_ZONE_SETPOINT, "null", 16)

        await self.bacnet_write(AHU_IP, AHU_OCCUPANCY, "null", 16)
        print("Released all BACnet overrides.")

    def transition_to(self, new_state):
        """FSM state transition with validation."""
        if can_transition(self.state, new_state):
            print(f"Transitioning from {self.state.value} to {new_state.value}")
            self.state = new_state
        else:
            print(f"Invalid transition from {self.state.value} to {new_state.value}")


async def main():
    bot = BuildingFSM()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
