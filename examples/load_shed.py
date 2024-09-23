import asyncio
from easy_aso import EasyASO

# BACnet configuration
POWER_MTR_BACNET_ADDR = "10.200.200.233"
POWER_MTR_BACNET_OBJ_ID = "analog-input,7"
POWER_THRESHOLD = 120.0  # kW threshold

AHU_COOL_VALVE_BACNET_ADDR = "10.200.200.233"
AHU_COOL_VALVE_BACNET_OBJ_ID = "analog-output,3"
AHU_COOL_VALVE_WRITE_VALUE = 0.0
AHU_COOL_VALVE_RELEASE_VALUE = "null"
AHU_COOL_VALVE_WRITE_PRIORITY = 10

SLEEP_INTERVAL_SECONDS = 60  # 1-minute interval
DUTY_CYCLE_INTERVAL_SECONDS = 900  # 15-minute interval


class CustomBot(EasyASO):
    def __init__(self):
        super().__init__()
        self.last_operation_time = 0

    async def on_start(self):
        print("CustomBot started. Monitoring power consumption.")
        initial_power = await self.do_read(
            POWER_MTR_BACNET_ADDR, POWER_MTR_BACNET_OBJ_ID
        )
        print(f"Initial power reading: {initial_power} kW")

    async def on_step(self):
        current_time = asyncio.get_event_loop().time()
        power_reading = await self.do_read(
            POWER_MTR_BACNET_ADDR, POWER_MTR_BACNET_OBJ_ID
        )
        print(f"Current power reading: {power_reading} kW")

        if current_time - self.last_operation_time < DUTY_CYCLE_INTERVAL_SECONDS:
            time_remaining = int(
                DUTY_CYCLE_INTERVAL_SECONDS - (current_time - self.last_operation_time)
            )
            print(
                f"Waiting for short cycle prevention. Time remaining: {time_remaining} seconds."
            )
        else:
            if power_reading > POWER_THRESHOLD:
                print(
                    f"Power {power_reading} exceeds threshold. Lowering AHU cool valve."
                )
                await self.do_write(
                    AHU_COOL_VALVE_BACNET_ADDR,
                    AHU_COOL_VALVE_BACNET_OBJ_ID,
                    AHU_COOL_VALVE_WRITE_VALUE,
                    AHU_COOL_VALVE_WRITE_PRIORITY,
                )
                self.last_operation_time = current_time
            elif power_reading <= POWER_THRESHOLD:
                print(
                    f"Power {power_reading} is below threshold. Releasing control of AHU cool valve."
                )
                await self.do_write(
                    AHU_COOL_VALVE_BACNET_ADDR,
                    AHU_COOL_VALVE_BACNET_OBJ_ID,
                    AHU_COOL_VALVE_RELEASE_VALUE,
                    AHU_COOL_VALVE_WRITE_PRIORITY,
                )
                self.last_operation_time = current_time

        await asyncio.sleep(SLEEP_INTERVAL_SECONDS)

    async def on_stop(self):
        print("CustomBot is stopping. Cleaning up resources...")


async def main():
    bot = CustomBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
