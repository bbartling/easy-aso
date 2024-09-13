import asyncio
from easy_aso import EasyASO

# BACnet configuration constants
POWER_MTR_BACNET_ADDR = "10.200.200.233"
POWER_MTR_BACNET_OBJ_ID = "analog-input,1"
POWER_THRESHOLD = 80.0  # kW

CHILLER_BACNET_ADDR = "10.200.200.233"
CHILLER_BACNET_OBJ_ID = "analog-value,12"
CHILLER_WRITE_VALUE = 0.0
CHILLER_RELEASE_VALUE = "null"
CHILLER_WRITE_PRIORITY = 10

# Time constants
SLEEP_INTERVAL_SECONDS = 60
DUTY_CYCLE_INTERVAL_SECONDS = 900  # 15 minutes

async def monitor_building_power(app):
    last_operation_time = 0  # Initialized to 0

    while True:
        building_power = await app.do_read(
            POWER_MTR_BACNET_ADDR, POWER_MTR_BACNET_OBJ_ID
        )
        print("Building power is", building_power)

        current_time = asyncio.get_event_loop().time()
        if current_time - last_operation_time < DUTY_CYCLE_INTERVAL_SECONDS:
            print(
                f"Waiting for short cycle prevention timer.\n"
                f"Time remaining: {int(DUTY_CYCLE_INTERVAL_SECONDS - (current_time - last_operation_time))} seconds."
            )
        else:
            if building_power and building_power > POWER_THRESHOLD:
                print(
                    f"Building power is {building_power}, exceeding threshold.\n"
                    f"Lowering setpoint..."
                )
                await app.do_write(
                    CHILLER_BACNET_ADDR,
                    CHILLER_BACNET_OBJ_ID,
                    CHILLER_WRITE_VALUE,
                    CHILLER_WRITE_PRIORITY,
                )
                last_operation_time = current_time
            elif building_power and building_power <= POWER_THRESHOLD:
                print(
                    f"Building power is {building_power}, below threshold.\n"
                    f"Releasing control..."
                )
                await app.do_write(
                    CHILLER_BACNET_ADDR,
                    CHILLER_BACNET_OBJ_ID,
                    CHILLER_RELEASE_VALUE,
                    CHILLER_WRITE_PRIORITY,
                )
                last_operation_time = current_time

        await asyncio.sleep(SLEEP_INTERVAL_SECONDS)

async def main():
    await EasyASO().run(monitor_building_power)

if __name__ == "__main__":
    asyncio.run(main())
