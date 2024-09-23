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

# VAV box addresses on MSTP trunk 100
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

# Define zone temperature setpoints
UNOCCUPIED_HEAT_SETPOINT = 55.0
UNOCCUPIED_COOL_SETPOINT = 90.0
OCCUPIED_HEAT_SETPOINT = 70.0
OCCUPIED_COOL_SETPOINT = 75.0

# Time interval (seconds)
SLEEP_INTERVAL_SECONDS = 60


class BuildingBot:
    def __init__(self):
        self.heat_setpoint = UNOCCUPIED_HEAT_SETPOINT
        self.cool_setpoint = UNOCCUPIED_COOL_SETPOINT

    async def on_start(self):
        print("BuildingBot started! Monitoring building HVAC system.")

    def is_occupied(self):
        """Check if the building is occupied based on the current time."""
        current_time = datetime.now().time()
        occupied_start = datetime.strptime(BUILDING_STARTUP, "%H:%M").time()
        occupied_end = datetime.strptime(BUILDING_SHUTDOWN, "%H:%M").time()
        return occupied_start <= current_time <= occupied_end

    async def adjust_setpoints(self, app):
        """Set VAV heat and cool setpoints based on occupancy."""
        if self.is_occupied():
            self.heat_setpoint = OCCUPIED_HEAT_SETPOINT
            self.cool_setpoint = OCCUPIED_COOL_SETPOINT
            print("Building is occupied: Setting occupied setpoints.")
        else:
            self.heat_setpoint = UNOCCUPIED_HEAT_SETPOINT
            self.cool_setpoint = UNOCCUPIED_COOL_SETPOINT
            print("Building is unoccupied: Setting unoccupied setpoints.")

        # Write temperature setpoints to each VAV
        for address in VAV_ADDRESSES:
            heat_obj_id = f"analog-value,1"
            cool_obj_id = f"analog-value,2"

            print(f"Writing heat setpoint {self.heat_setpoint} to {address}")
            await app.do_write(address, heat_obj_id, self.heat_setpoint, 16)

            print(f"Writing cool setpoint {self.cool_setpoint} to {address}")
            await app.do_write(address, cool_obj_id, self.cool_setpoint, 16)

    async def update_outside_air_temp(self, app):
        """Read outside air temperature from the boiler and send to AHU."""
        outside_air_temp = await app.do_read(BOILER_IP, BOILER_OUTSIDE_AIR_SENSOR)
        print(f"Boiler outside air temperature: {outside_air_temp}")

        # Write the outside air temperature to the AHU
        print(f"Writing outside air temperature {outside_air_temp} to AHU")
        await app.do_write(AHU_IP, AHU_OUTSIDE_AIR_VALUE, outside_air_temp, 16)

    async def on_step(self, app):
        """Main loop (iteration) for the building bot control."""
        print("Starting step...")
        await self.adjust_setpoints(app)
        await self.update_outside_air_temp(app)
        print("Step complete.")

    async def control_building_hvac(self, app):
        """Continuously run the HVAC control steps like SC2's bot steps."""
        await self.on_start()
        while True:
            await self.on_step(app)
            await asyncio.sleep(SLEEP_INTERVAL_SECONDS)


async def main():
    building_bot = BuildingBot()
    await EasyASO().run(building_bot.control_building_hvac)


if __name__ == "__main__":
    asyncio.run(main())
