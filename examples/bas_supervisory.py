import asyncio
from easy_aso import EasyASO
from datetime import datetime

"""
Not tested yet but its a simple script
that replicates a common BAS to run
equipment on a schedule and share the
outside air temp value from the boiler
to an AHU.
"""

# BACnet configuration constants
BUILDING_STARTUP = "08:00"
BUILDING_SHUTDOWN = "18:00"
BOILER_IP = "192.168.0.102"
AHU_IP = "192.168.0.103"
BOILER_OUTSIDE_AIR_SENSOR = "analog-input,3"
AHU_OUTSIDE_AIR_VALUE = "analog-value,10"

# VAV box addresses on MSTP trunk 100
vav_addresses = [
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
unoccupied_heat_setpoint = 55.0
unoccupied_cool_setpoint = 90.0
occupied_heat_setpoint = 70.0
occupied_cool_setpoint = 75.0


# Function to check if building is occupied
def is_occupied():
    current_time = datetime.now().time()
    occupied_start = datetime.strptime(BUILDING_STARTUP, "%H:%M").time()
    occupied_end = datetime.strptime(BUILDING_SHUTDOWN, "%H:%M").time()
    return occupied_start <= current_time <= occupied_end


# Main control logic for the building HVAC
async def control_building_hvac(app):
    while True:
        if is_occupied():
            heat_setpoint = occupied_heat_setpoint
            cool_setpoint = occupied_cool_setpoint
        else:
            heat_setpoint = unoccupied_heat_setpoint
            cool_setpoint = unoccupied_cool_setpoint

        # Write temperature setpoints to each VAV
        for address in vav_addresses:
            heat_obj_id = f"analog-value,1"
            cool_obj_id = f"analog-value,2"

            print(f"Writing heat setpoint {heat_setpoint} to {address}")
            await app.do_write(address, heat_obj_id, heat_setpoint, 16)

            print(f"Writing cool setpoint {cool_setpoint} to {address}")
            await app.do_write(address, cool_obj_id, cool_setpoint, 16)

        # Read outside air temperature from the boiler
        outside_air_temp = await app.do_read(BOILER_IP, BOILER_OUTSIDE_AIR_SENSOR)
        print(f"Outside air temperature is {outside_air_temp}")

        # Write the outside air temperature to the AHU controller
        print(f"Writing outside air temperature {outside_air_temp} to AHU")
        await app.do_write(AHU_IP, AHU_OUTSIDE_AIR_VALUE, outside_air_temp, 16)

        # Sleep for 1 minute
        await asyncio.sleep(60)


async def main():
    await EasyASO().run(control_building_hvac)


if __name__ == "__main__":
    asyncio.run(main())
