import asyncio
from easy_aso import EasyASO
from datetime import datetime

# BACnet configuration constants
BUILDING_STARTUP = "08:00"
BUILDING_SHUTDOWN = "18:00"

BOILER_IP = "10.200.200.233"
BOILER_OUTSIDE_AIR_SENSOR = "analog-input,1"

AHU_IP = "10.200.200.233"
AHU_OUTSIDE_AIR_VALUE = "analog-value,2"
AHU_OCCUPANCY = "multistate-value,1"

VAV_ADDRESSES = [
    # all the same address for sim purposes
    "10.200.200.233",
    "10.200.200.233",
    "10.200.200.233",
    "10.200.200.233",
    "10.200.200.233",
    "10.200.200.233",
    "10.200.200.233",
    "10.200.200.233",
    "10.200.200.233",
    "10.200.200.233",
]

UNOCCUPIED_HEAT_SETPOINT = 55.0
UNOCCUPIED_COOL_SETPOINT = 90.0
OCCUPIED_HEAT_SETPOINT = 70.0
OCCUPIED_COOL_SETPOINT = 75.0
VAV_ZONE_SETPOINT = "analog-value,3"

SLEEP_INTERVAL_SECONDS = 300


class BuildingBot(EasyASO):
    def __init__(self):
        super().__init__()
        self.heat_setpoint = UNOCCUPIED_HEAT_SETPOINT
        self.cool_setpoint = UNOCCUPIED_COOL_SETPOINT

    async def on_start(self):
        print("BuildingBot started! Monitoring building HVAC system.")

    async def on_stop(self):
        print("BuildingBot is stopping. Cleaning up resources...")

    def is_occupied(self):
        current_time = datetime.now().time()
        occupied_start = datetime.strptime(BUILDING_STARTUP, "%H:%M").time()
        occupied_end = datetime.strptime(BUILDING_SHUTDOWN, "%H:%M").time()
        return occupied_start <= current_time <= occupied_end

    async def adjust_setpoints(self):
        if self.is_occupied():
            self.heat_setpoint = OCCUPIED_HEAT_SETPOINT
            self.cool_setpoint = OCCUPIED_COOL_SETPOINT
            print("Building is occupied: Setting occupied setpoints.")
        else:
            self.heat_setpoint = UNOCCUPIED_HEAT_SETPOINT
            self.cool_setpoint = UNOCCUPIED_COOL_SETPOINT
            print("Building is unoccupied: Setting unoccupied setpoints.")

        for address in VAV_ADDRESSES:
            response = await self.bacnet_write(
                address, VAV_ZONE_SETPOINT, self.heat_setpoint, 16
            )
            if response is None:
                print(f"Setpoint write successful for VAV at {address}.")
            else:
                print(
                    f"Setpoint write failed for VAV at {address} with error: {response}"
                )

    async def update_outside_air_temp(self):
        outside_air_temp = await self.bacnet_read(BOILER_IP, BOILER_OUTSIDE_AIR_SENSOR)

        if outside_air_temp is None:
            print(f"Failed to read boiler outside air temperature from {BOILER_IP}.")
        else:
            print(f"Boiler outside air temperature: {outside_air_temp}")
            response = await self.bacnet_write(
                AHU_IP, AHU_OUTSIDE_AIR_VALUE, outside_air_temp, 16
            )

            if response is None:
                print("Outside air temperature written successfully to AHU.")
            else:
                print(
                    f"Failed to write outside air temperature to AHU with error: {response}"
                )

    async def on_step(self):
        await self.adjust_setpoints()
        await self.update_outside_air_temp()
        await asyncio.sleep(SLEEP_INTERVAL_SECONDS)


async def main():
    bot = BuildingBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
