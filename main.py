import BAC0
import time
from datetime import datetime

# Initialize BACnet
bacnet = BAC0.lite()

# Define constants
BUILDING_STARTUP = "08:00"
BUILDING_SHUTDOWN = "18:00"

# Boiler and AHU details
BOILER_IP = "192.168.0.102/24"
AHU_IP = "192.168.0.103/24"
BOILER_OUTSIDE_AIR_SENSOR = "analogInput 3 presentValue"
AHU_OUTSIDE_AIR_VALUE = "analogValue 10 presentValue"

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


# Main loop for supervisory control
while True:
    if is_occupied():
        heat_setpoint = occupied_heat_setpoint
        cool_setpoint = occupied_cool_setpoint
    else:
        heat_setpoint = unoccupied_heat_setpoint
        cool_setpoint = unoccupied_cool_setpoint

    # Write temperature setpoints to each VAV
    for address in vav_addresses:
        write_heat = f"{address} analogValue 1 presentValue {heat_setpoint}"
        bacnet.write(write_heat)

        write_cool = f"{address} analogValue 2 presentValue {cool_setpoint}"
        bacnet.write(write_cool)

    # Read outside air temperature from the boiler
    outside_air_temp = bacnet.read(f"{BOILER_IP} {BOILER_OUTSIDE_AIR_SENSOR}")

    # Write the outside air temperature to the AHU controller
    bacnet.write(f"{AHU_IP} {AHU_OUTSIDE_AIR_VALUE} {outside_air_temp}")

    # Sleep for 1 minute
    time.sleep(60)

# Clean up BACnet connection
bacnet.disconnect()
