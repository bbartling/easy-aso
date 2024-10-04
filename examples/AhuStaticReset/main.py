import asyncio
from easy_aso import EasyASO
from enum import Enum
from datetime import datetime, timedelta
from definitions import VavDefinition, AhuDefinition


# Define FSM States for AHUBot Control
class AHUState(Enum):
    IDLE = "idle"
    MONITORING_OCCUPIED = "monitoring_occupied"
    MONITORING_UNOCCUPIED = "monitoring_unoccupied"
    ADJUSTING = "adjusting"
    RELEASE_OVERRIDE = "release_override"


# Schedule and AHU operation times
BUILDING_STARTUP = "08:00"
BUILDING_SHUTDOWN = "18:00"

# Updated optimization schedule hard coded
OPTIMIZATION_SCHEDULE = {
    0: True,  # Monday
    1: True,  # Tuesday
    2: True,  # Wednesday
    3: True,  # Thursday
    4: True,  # Friday
    5: False,  # Saturday
    6: False,  # Sunday
}

# FSM Transitions for AHU Management
transitions = {
    AHUState.IDLE: [AHUState.MONITORING_OCCUPIED, AHUState.MONITORING_UNOCCUPIED],
    AHUState.MONITORING_OCCUPIED: [AHUState.ADJUSTING, AHUState.RELEASE_OVERRIDE],
    AHUState.MONITORING_UNOCCUPIED: [AHUState.ADJUSTING, AHUState.RELEASE_OVERRIDE],
    AHUState.ADJUSTING: [AHUState.RELEASE_OVERRIDE],
    AHUState.RELEASE_OVERRIDE: [AHUState.IDLE],
}


# Check if a transition is allowed between states
def can_transition(current_state, next_state):
    return next_state in transitions.get(current_state, [])


class AHUBot(EasyASO):
    def __init__(self, ahu_configs):
        super().__init__()
        self.ahu_configs = ahu_configs
        self.last_release_time = datetime.now()
        self.state = AHUState.IDLE  # Initialize with IDLE state

    async def on_start(self):
        print("AHU Bot started! Managing multiple AHUs.")
        self.transition_to(AHUState.MONITORING_OCCUPIED)

    async def on_stop(self):
        print("AHU Bot stopping. Cleaning up resources...")
        await self.release_all()

    def is_occupied(self):
        current_time = datetime.now().time()
        current_day = datetime.now().weekday()

        if OPTIMIZATION_SCHEDULE.get(current_day, False):
            occupied_start = datetime.strptime(BUILDING_STARTUP, "%H:%M").time()
            occupied_end = datetime.strptime(BUILDING_SHUTDOWN, "%H:%M").time()
            return occupied_start <= current_time <= occupied_end

        return False

    async def handle_state(self):
        """Handle the state transitions and corresponding actions."""
        if self.state == AHUState.MONITORING_OCCUPIED:
            await self.monitor_occupied_ahus()
        elif self.state == AHUState.MONITORING_UNOCCUPIED:
            await self.monitor_unoccupied_ahus()
        elif self.state == AHUState.ADJUSTING:
            await self.adjust_ahu_settings()
        elif self.state == AHUState.RELEASE_OVERRIDE:
            await self.release_all()
            self.transition_to(AHUState.IDLE)

    def transition_to(self, new_state):
        """Transition to a new state with validation."""
        if can_transition(self.state, new_state):
            print(f"Transitioning from {self.state.value} to {new_state.value}")
            self.state = new_state
        else:
            print(f"Invalid transition from {self.state.value} to {new_state.value}.")

    async def monitor_occupied_ahus(self):
        """Manage AHUs when the building is occupied."""
        print("Monitoring occupied building AHUs...")
        for ahu in self.ahu_configs:
            fan_running = await self.check_fan_running(ahu)
            if fan_running:
                vav_data = await self.read_vav_data(ahu)
                await self.adjust_static_pressure(ahu, vav_data)
            else:
                print(f"Fan is not running on AHU {ahu.ip}, skipping control.")
        # Transition to adjusting state
        self.transition_to(AHUState.ADJUSTING)

    async def monitor_unoccupied_ahus(self):
        """Manage AHUs when the building is unoccupied."""
        print("Monitoring unoccupied building AHUs...")
        # Implement logic for unoccupied building AHU management
        for ahu in self.ahu_configs:
            print(
                f"Skipping adjustments for AHU {ahu.ip} since building is unoccupied."
            )
        # Transition to adjusting state
        self.transition_to(AHUState.ADJUSTING)

    async def adjust_ahu_settings(self):
        """Adjust AHU settings after monitoring."""
        print("Adjusting AHU setpoints...")
        # Simulate adjusting AHU settings
        for ahu in self.ahu_configs:
            print(f"Adjusting static pressure for AHU {ahu.ip}")
        # After adjusting, release overrides and reset state
        self.transition_to(AHUState.RELEASE_OVERRIDE)

    async def release_all(self):
        """Releases the duct static pressure setpoint for each AHU."""
        for ahu in self.ahu_configs:
            await self.bacnet_write(ahu.ip, ahu.static_pressure_obj_id, "null", 16)
            print(f"Released duct static pressure setpoint for AHU {ahu.ip}")

    async def check_fan_running(self, ahu):
        fan_speed = await self.bacnet_read(ahu.ip, ahu.fan_speed_obj_id)
        return fan_speed > ahu.FAN_MIN_SPEED

    async def read_vav_data(self, ahu):
        vav_data = []
        for vav in ahu.vav_configs:
            damper_position = await self.bacnet_read(
                vav.address, vav.damper_position_obj_id
            )
            airflow = await self.bacnet_read(vav.address, vav.airflow_obj_id)
            airflow_setpoint = await self.bacnet_read(
                vav.address, vav.airflow_setpoint_obj_id
            )
            vav_data.append((damper_position, airflow, airflow_setpoint))
        return vav_data

    async def adjust_static_pressure(self, ahu, vav_data):
        """Simulate static pressure adjustment."""
        print(f"Adjusting static pressure for AHU {ahu.ip}")
        await asyncio.sleep(1)  # Simulating adjustment


# VAV configuration for each AHU
vav_configs_ahu_1 = [
    VavDefinition(
        address="10.200.200.233",
        damper_position_obj_id="analog-input,8",
        airflow_obj_id="analog-input,1",
        airflow_setpoint_obj_id="analog-value,4",
    ),
]

# AHU configuration with tuning parameters
ahu_configs = [
    AhuDefinition(
        ip="10.200.200.233",
        fan_speed_obj_id="analog-output,1",
        static_pressure_obj_id="analog-value,1",
        vav_configs=vav_configs_ahu_1,
        SP0=1.5,
        SPmin=0.5,
        SPmax=3.0,
        SPtrim=-0.1,
        SPres=0.2,
        SPres_max=1.0,
        I=1,
        FAN_MIN_SPEED=15.0,
    ),
]


async def main():
    bot = AHUBot(ahu_configs)
    while True:
        await bot.handle_state()  # Run FSM loop
        await asyncio.sleep(2)  # Sleep for 2 seconds before handling next state


if __name__ == "__main__":
    asyncio.run(main())
