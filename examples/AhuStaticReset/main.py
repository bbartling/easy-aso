import asyncio
from easy_aso import EasyASO
from datetime import datetime

from definitions import VavDefinition, AhuDefinition


"""
only run optimization during a scheduled times
AHU should run as needed during cycling 
during unoccupied times

A BAS schedule could also be linked up to the
optimization_status BACnet server point too!
"""

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


class AHUBot(EasyASO):
    def __init__(self, ahu_configs):
        super().__init__()
        self.ahu_configs = ahu_configs  # List of AHUConfig instances

    async def on_start(self):
        print("AHU Bot started! Managing multiple AHUs.")
        for ahu in self.ahu_configs:
            print(
                f"Initial static pressure setpoint for AHU {ahu.ip} is {ahu.current_sp}"
            )

    async def on_step(self):
        optimization_status = self.get_optimization_enabled_status()

        if not optimization_status:
            await self.release_all()
        else:
            for ahu in self.ahu_configs:
                if self.is_occupied():
                    await self.manage_ahu(ahu)
                else:
                    print(
                        f"Building is unoccupied.\n"
                        f"Skipping pressure control for AHU {ahu.ip}."
                    )

        await asyncio.sleep(60)

    async def on_stop(self):
        print("AHU Bot stopping. Cleaning up resources...")
        await self.release_all()

    def is_occupied(self):
        """Checks if the building is within occupied hours based on the schedule."""
        current_time = datetime.now().time()
        current_day = datetime.now().weekday()

        if OCCUPANCY_SCHEDULE.get(current_day, False):
            occupied_start = datetime.strptime(BUILDING_STARTUP, "%H:%M").time()
            occupied_end = datetime.strptime(BUILDING_SHUTDOWN, "%H:%M").time()
            return occupied_start <= current_time <= occupied_end

        return False  # Not occupied on days marked as False

    async def manage_ahu(self, ahu):
        fan_running = await self.check_fan_running(ahu)
        if fan_running:
            print(
                f"Fan is running on AHU {ahu.ip}.\n" "Proceeding with pressure control."
            )

            vav_data = await self.read_vav_data(ahu)
            await self.adjust_static_pressure(ahu, vav_data)
        else:
            print(
                f"Fan is not running on AHU {ahu.ip}.\n"
                "Skipping pressure control this step."
            )

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
        total_reset_requests = 0
        vav_data.sort(reverse=True, key=lambda x: x[0])

        vav_data = vav_data[ahu.I :]  # Ignore top I VAVs

        for damper_position, airflow, airflow_setpoint in vav_data:
            if airflow_setpoint > 0 and damper_position > 95:
                if airflow < 0.5 * airflow_setpoint:
                    total_reset_requests += 3
                elif airflow < 0.7 * airflow_setpoint:
                    total_reset_requests += 2
                else:
                    total_reset_requests += 1

        if total_reset_requests > 0:
            if ahu.total_pressure_increase < ahu.SPres_max:
                pressure_increase = min(
                    ahu.SPres, ahu.SPres_max - ahu.total_pressure_increase
                )
                ahu.current_sp = min(ahu.current_sp + pressure_increase, ahu.SPmax)
                ahu.total_pressure_increase += pressure_increase
                print(
                    f"Pressure increased on AHU {ahu.ip} to {ahu.current_sp}.\n"
                    "Adjusting static pressure."
                )

            else:
                print(
                    f"Maximum pressure increase ({ahu.SPres_max}) reached on AHU {ahu.ip}.\n"
                    "No further pressure adjustment."
                )

        else:
            ahu.current_sp = max(ahu.current_sp + ahu.SPtrim, ahu.SPmin)
            print(
                f"Pressure trimmed on AHU {ahu.ip} to {ahu.current_sp}.\n"
                "Reducing static pressure."
            )

        await self.bacnet_write(ahu.ip, ahu.static_pressure_obj_id, ahu.current_sp, 16)

    async def release_all(self):
        """Releases the duct static pressure setpoint for each AHU."""
        for ahu in self.ahu_configs:
            await self.bacnet_write(ahu.ip, ahu.static_pressure_obj_id, "null", 16)
            print(f"Released duct static pressure setpoint for AHU {ahu.ip}")


# VAV configuration for each AHU
vav_configs_ahu_1 = [
    VavDefinition(
        address="10.200.200.233",
        damper_position_obj_id="analog-input,8",
        airflow_obj_id="analog-input,1",
        airflow_setpoint_obj_id="analog-value,4",
    ),
    VavDefinition(
        address="10.200.200.233",
        damper_position_obj_id="analog-input,8",
        airflow_obj_id="analog-input,1",
        airflow_setpoint_obj_id="analog-value,4",
    ),
    # Add more VAVs as needed
]

# AHU configuration with individual tuning parameters
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
    # Add more AHUs with different tuning as needed
]


async def main():
    bot = AHUBot(ahu_configs)
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
