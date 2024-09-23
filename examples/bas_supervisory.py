import asyncio
from easy_aso import EasyASO
from datetime import datetime

# BACnet configuration constants
BUILDING_STARTUP = "08:00"
BUILDING_SHUTDOWN = "18:00"
BOILER_IP = "192.168.0.102"
AHU_IP = "192.168.0.103"
BOILER_OUTSIDE_AIR_SENSOR = "analog-input,3"
AHU_OUTSIDE_AIR_VALUE = "analog-value,10"

VAV_ADDRESSES = [
    "100:1",
    "100:2",
    "100:3",
    "100:4",
    "100:5",
    "100:6",
    "100:7",
    "100:8",
    "100:9",
    "100:10",
]

UNOCCUPIED_HEAT_SETPOINT = 55.0
UNOCCUPIED_COOL_SETPOINT = 90.0
OCCUPIED_HEAT_SETPOINT = 70.0
OCCUPIED_COOL_SETPOINT = 75.0
SLEEP_INTERVAL_SECONDS = 60


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
            heat_obj_id = f"analog-value,1"
            cool_obj_id = f"analog-value,2"

            await self.do_write(address, heat_obj_id, self.heat_setpoint, 16)
            await self.do_write(address, cool_obj_id, self.cool_setpoint, 16)

    async def update_outside_air_temp(self):
        outside_air_temp = await self.do_read(BOILER_IP, BOILER_OUTSIDE_AIR_SENSOR)
        print(f"Boiler outside air temperature: {outside_air_temp}")
        await self.do_write(AHU_IP, AHU_OUTSIDE_AIR_VALUE, outside_air_temp, 16)

    async def on_step(self):
        await self.adjust_setpoints()
        await self.update_outside_air_temp()
        await asyncio.sleep(SLEEP_INTERVAL_SECONDS)


async def main():
    bot = BuildingBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
