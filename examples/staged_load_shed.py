import asyncio
from easy_aso import EasyASO

"""
$ python examples/staged_load_shed.py --name easy-aso --instance 987654
"""

# BACnet configuration constants
POWER_MTR_BACNET_ADDR = "10.200.200.233"
POWER_MTR_BACNET_OBJ_ID = "analog-input,7"
POWER_THRESHOLD = 120.0  # a fake kW setpoint

# Stage 1 - Reset zone setpoints upward
VAV_ZONE_BACNET_ADDRS = [
    "10.200.200.233",  # VAV1
    "10.200.200.233",  # VAV2
    "10.200.200.233",  # VAV3
    "10.200.200.233",  # VAV4
    "10.200.200.233",  # VAV5
]
VAV_ZONE_STP_BACNET_OBJ_ID = "analog-value,2"
VAV_ZONE_STP_WRITE_VALUE = 78.0  # deg F
VAV_ZONE_STP_RELEASE_VALUE = "null"
VAV_ZONE_STP_WRITE_PRIORITY = 10

# Stage 2 - Turn off non-essential lighting
LIGHTING_SYS_BACNET_ADDR = "10.200.200.233"
LIGHTING_SYS_BACNET_OBJ_ID = "analog-value,3"
LIGHTING_SYS_WRITE_VALUE = 50.0
LIGHTING_SYS_RELEASE_VALUE = "null"
LIGHTING_SYS_WRITE_PRIORITY = 10

# Stage 3 - Capacity limit cooling system
AHU_COOL_VALVE_BACNET_ADDR = "10.200.200.233"
AHU_COOL_VALVE_BACNET_OBJ_ID = "analog-output,3"
AHU_COOL_VALVE_WRITE_VALUE = 0.0
AHU_COOL_VALVE_RELEASE_VALUE = "null"
AHU_COOL_VALVE_WRITE_PRIORITY = 10

# Time constants
SLEEP_INTERVAL_SECONDS = 60
DUTY_CYCLE_INTERVAL_SECONDS = 900  # 15 minutes
STAGE_UP_DOWN_TIMER = 300  # 5 minutes for staging timer


async def monitor_building_power(app):
    last_operation_time = 0
    current_stage = 0  # Track the current stage of load shedding

    while True:
        # Using the getter to print the optimization enabled status as a boolean
        print(f"Opt Enabled BV Status bool: {app.get_optimization_enabled_status()}")

        building_power = await app.do_read(
            POWER_MTR_BACNET_ADDR, POWER_MTR_BACNET_OBJ_ID
        )
        print("Building power is", building_power)

        current_time = asyncio.get_event_loop().time()
        time_elapsed = current_time - last_operation_time
        
        # Adjust the calculation for stage_timer_remaining to avoid negative values
        if time_elapsed < STAGE_UP_DOWN_TIMER:
            stage_timer_remaining = int(STAGE_UP_DOWN_TIMER - time_elapsed)
        else:
            stage_timer_remaining = 0  # Set to 0 to indicate no time left

        if building_power > POWER_THRESHOLD:
            # If power is above the threshold, move through stages
            if time_elapsed >= STAGE_UP_DOWN_TIMER:
                # Move to the next stage if the stage timer has expired
                if current_stage < 3:
                    current_stage += 1
                    last_operation_time = current_time  # Update to current time
                    print(f"Initiating Stage {current_stage}")
                    await initiate_stage(app, current_stage)
                else:
                    print(f"Stage {current_stage} is already at maximum level.")

            print(
                f"Waiting for stage up/down timer.\n"
                f"Time remaining: {stage_timer_remaining} seconds."
            )

        elif building_power <= POWER_THRESHOLD:
            # If power drops below the threshold, start releasing stages
            if current_stage > 0 and time_elapsed >= STAGE_UP_DOWN_TIMER:
                current_stage -= 1
                last_operation_time = current_time  # Update to current time
                print(f"Releasing Stage {current_stage + 1}")
                await release_stage(app, current_stage + 1)
            elif current_stage == 0:
                print("All stages released. Building power is below threshold.")

        await asyncio.sleep(SLEEP_INTERVAL_SECONDS)



async def initiate_stage(app, stage):
    """
    Initiate the given stage of load shedding.
    """
    if stage == 1:
        print("Stage 1: Resetting zone setpoints upward.")
        for addr in VAV_ZONE_BACNET_ADDRS:
            await app.do_write(
                addr,
                VAV_ZONE_STP_BACNET_OBJ_ID,
                VAV_ZONE_STP_WRITE_VALUE,
                VAV_ZONE_STP_WRITE_PRIORITY,
            )
    elif stage == 2:
        print("Stage 2: Turning off non-essential lighting.")
        await app.do_write(
            LIGHTING_SYS_BACNET_ADDR,
            LIGHTING_SYS_BACNET_OBJ_ID,
            LIGHTING_SYS_WRITE_VALUE,
            LIGHTING_SYS_WRITE_PRIORITY,
        )
    elif stage == 3:
        print("Stage 3: Limiting cooling system capacity.")
        await app.do_write(
            AHU_COOL_VALVE_BACNET_ADDR,
            AHU_COOL_VALVE_BACNET_OBJ_ID,
            AHU_COOL_VALVE_WRITE_VALUE,
            AHU_COOL_VALVE_WRITE_PRIORITY,
        )

async def release_stage(app, stage):
    """
    Release the given stage of load shedding.
    """
    if stage == 1:
        print("Releasing Stage 1: Resetting zone setpoints to normal.")
        for addr in VAV_ZONE_BACNET_ADDRS:
            await app.do_write(
                addr,
                VAV_ZONE_STP_BACNET_OBJ_ID,
                VAV_ZONE_STP_RELEASE_VALUE,
                VAV_ZONE_STP_WRITE_PRIORITY,
            )
    elif stage == 2:
        print("Releasing Stage 2: Turning on non-essential lighting.")
        await app.do_write(
            LIGHTING_SYS_BACNET_ADDR,
            LIGHTING_SYS_BACNET_OBJ_ID,
            LIGHTING_SYS_RELEASE_VALUE,
            LIGHTING_SYS_WRITE_PRIORITY,
        )
    elif stage == 3:
        print("Releasing Stage 3: Allowing full cooling system capacity.")
        await app.do_write(
            AHU_COOL_VALVE_BACNET_ADDR,
            AHU_COOL_VALVE_BACNET_OBJ_ID,
            AHU_COOL_VALVE_RELEASE_VALUE,
            AHU_COOL_VALVE_WRITE_PRIORITY,
        )

async def main():
    await EasyASO().run(monitor_building_power)

if __name__ == "__main__":
    asyncio.run(main())
