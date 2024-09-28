import asyncio
from easy_aso import EasyASO
from datetime import datetime, timedelta

# BACnet configuration constants
BOILER_IP = "10.200.200.233"
BOILER_OUTSIDE_AIR_SENSOR = "analog-input,1"

AHU_IP = "10.200.200.233"
AHU_OUTSIDE_AIR_VALUE = "analog-value,2"
AHU_OCCUPANCY = "multi-state-value,1"
AHU_ZONE_TEMP = "analog-value,5"

VAV_ADDRESSES = [
    "10.200.200.233",
    "10.200.200.233",
    "10.200.200.233",
]

UNOCCUPIED_HEAT_SETPOINT = 60.0
OCCUPIED_HEAT_SETPOINT = 72.0
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


class BuildingBot(EasyASO):
    def __init__(self):
        super().__init__()
        self.heat_setpoint = UNOCCUPIED_HEAT_SETPOINT
        self.last_outside_air_update = (
            datetime.now()
        )  # Using datetime instead of epoch time
        self.last_vav_temp_update = (
            datetime.now()
        )  # Using datetime instead of epoch time

    async def on_start(self):
        print("BuildingBot started! Monitoring building HVAC system.")

    async def on_stop(self):
        print("BuildingBot is stopping. Releasing all BACnet overrides.")
        await self.release_all()

    def is_occupied(self):
        """Check if the building is occupied based on time and day."""
        current_time = datetime.now().time()
        current_day = datetime.now().weekday()

        if OCCUPANCY_SCHEDULE.get(current_day, False):
            occupied_start = datetime.strptime(BUILDING_STARTUP, "%H:%M").time()
            occupied_end = datetime.strptime(BUILDING_SHUTDOWN, "%H:%M").time()
            return occupied_start <= current_time <= occupied_end

        return False  # Not occupied on days set to False in the schedule

    async def adjust_setpoints(self):
        if self.is_occupied():
            self.heat_setpoint = OCCUPIED_HEAT_SETPOINT
            ahu_occupancy_value = 1  # Occupied
            print(
                "Building is occupied: Setting occupied setpoints and AHU to occupied mode."
            )
        else:
            self.heat_setpoint = UNOCCUPIED_HEAT_SETPOINT
            ahu_occupancy_value = 2  # Unoccupied
            print(
                "Building is unoccupied: Setting unoccupied setpoints and AHU to unoccupied mode."
            )

        for address in VAV_ADDRESSES:
            await self.bacnet_write(address, VAV_ZONE_SETPOINT, self.heat_setpoint, 16)

        await self.bacnet_write(AHU_IP, AHU_OCCUPANCY, ahu_occupancy_value, 16)

    async def update_outside_air_temp(self, interval_seconds):
        current_time = datetime.now()
        if (current_time - self.last_outside_air_update) >= timedelta(
            seconds=interval_seconds
        ):
            outside_air_temp = await self.bacnet_read(
                BOILER_IP, BOILER_OUTSIDE_AIR_SENSOR
            )
            await self.bacnet_write(AHU_IP, AHU_OUTSIDE_AIR_VALUE, outside_air_temp, 16)
            self.last_outside_air_update = current_time

    async def average_vav_zone_temp_and_control_ahu(self, interval_seconds):
        current_time = datetime.now()
        if not self.is_occupied() and (
            current_time - self.last_vav_temp_update
        ) >= timedelta(seconds=interval_seconds):
            temperatures = []
            for address in VAV_ADDRESSES:
                temp = await self.bacnet_read(address, VAV_ZONE_AIR_TEMP)
                temperatures.append(temp)

            if temperatures:
                average_temp = sum(temperatures) / len(temperatures)
                print(
                    f"Average VAV zone temperature during unoccupied time: {average_temp}"
                )
                await self.bacnet_write(AHU_IP, AHU_ZONE_TEMP, average_temp, 16)
                self.last_vav_temp_update = current_time

    async def on_step(self):
        optimization_status = self.get_optimization_enabled_status()

        if not optimization_status:
            await self.release_all()
        else:
            await self.adjust_setpoints()
            await self.update_outside_air_temp(300)
            await self.average_vav_zone_temp_and_control_ahu(300)

        await asyncio.sleep(60)

    async def release_all(self):
        for address in VAV_ADDRESSES:
            await self.bacnet_write(address, VAV_ZONE_SETPOINT, "null", 16)

        await self.bacnet_write(AHU_IP, AHU_OCCUPANCY, "null", 16)
        print("All BACnet overrides have been released.")


async def main():
    bot = BuildingBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
