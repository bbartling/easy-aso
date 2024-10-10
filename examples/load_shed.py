from easy_aso import EasyASO
import asyncio
import time

# BACnet configuration
POWER_MTR_BACNET_ADDR = "10.200.200.233"
POWER_MTR_BACNET_OBJ_ID = "analog-input,7"
POWER_THRESHOLD = 120.0  # kW Setpoint for building

AHU_COOL_VALVE_BACNET_ADDR = "10.200.200.233"
AHU_COOL_VALVE_BACNET_OBJ_ID = "analog-output,3"
AHU_COOL_VALVE_WRITE_VALUE = 0.0
AHU_COOL_VALVE_WRITE_PRIORITY = 10

STEP_INTERVAL_SECONDS = 60
STAGE_UP_TIMER_SECONDS = 300
STAGE_DOWN_TIMER_SECONDS = 300


class CustomBot(EasyASO):
    def __init__(self, args=None):
        super().__init__(args)
        self.last_stage_up_time = time.time()
        self.last_stage_down_time = time.time()

    async def on_start(self):
        print("CustomBot started. Monitoring power consumption.")

    async def on_step(self):
        current_time = time.time()

        # Read power consumption with error handling
        try:
            power_reading = await self.bacnet_read(
                POWER_MTR_BACNET_ADDR, POWER_MTR_BACNET_OBJ_ID
            )
            if power_reading is None or isinstance(power_reading, str):
                raise ValueError(f"Invalid power reading: {power_reading}")
            print(f"Current power reading: {power_reading} kW")
        except Exception as e:
            print(f"ERROR: Failed to read power consumption: {e}")
            power_reading = None  # Set to None if there's an error

        # Get status of the discoverable BACnet point for optimization enabled
        try:
            optimization_status = self.get_optimization_enabled_status()
            print(f"Optimization Enabled Status: {optimization_status}")
        except Exception as e:
            print(f"ERROR: Failed to get optimization status: {e}")
            optimization_status = False  # Default to False if there's an error

        if not optimization_status:
            print("Optimization disabled, releasing all BACnet overrides.")
            await self.release_all()
        elif power_reading is not None:
            # Proceed only if power_reading is valid
            if power_reading > POWER_THRESHOLD:
                await self.handle_stage_up_logic(current_time, power_reading)
            else:
                await self.handle_stage_down_logic(current_time, power_reading)

        await asyncio.sleep(STEP_INTERVAL_SECONDS)

    async def handle_stage_up_logic(self, current_time, power_reading):
        stage_up_elapsed = current_time - self.last_stage_up_time
        print(f"Stage Up Timer: {stage_up_elapsed:.2f} seconds elapsed")

        if stage_up_elapsed >= STAGE_UP_TIMER_SECONDS:
            print(f"Power {power_reading} exceeds threshold.")
            print(f"Lowering AHU cool valve.")
            try:
                await self.bacnet_write(
                    AHU_COOL_VALVE_BACNET_ADDR,
                    AHU_COOL_VALVE_BACNET_OBJ_ID,
                    AHU_COOL_VALVE_WRITE_VALUE,
                    AHU_COOL_VALVE_WRITE_PRIORITY,
                )
                self.last_stage_up_time = current_time
            except Exception as e:
                print(f"ERROR: Failed to write AHU cool valve: {e}")
        else:
            time_remaining = int(STAGE_UP_TIMER_SECONDS - stage_up_elapsed)
            print(f"Waiting for stage up timer.")
            print(f"Time remaining: {time_remaining} seconds.")

    async def handle_stage_down_logic(self, current_time, power_reading):
        stage_down_elapsed = current_time - self.last_stage_down_time
        print(f"Stage Down Timer: {stage_down_elapsed:.2f} seconds elapsed")

        if stage_down_elapsed >= STAGE_DOWN_TIMER_SECONDS:
            print(f"Power {power_reading} is below threshold.")
            print(f"Releasing control of AHU cool valve.")
            try:
                await self.release_all()
                self.last_stage_down_time = current_time
            except Exception as e:
                print(f"ERROR: Failed to release control of AHU cool valve: {e}")
        else:
            time_remaining = int(STAGE_DOWN_TIMER_SECONDS - stage_down_elapsed)
            print(f"Waiting for stage down timer.")
            print(f"Time remaining: {time_remaining} seconds.")

    async def on_stop(self):
        print("on_stop called... Releasing all BACnet overrides.")
        try:
            await self.release_all()
        except Exception as e:
            print(f"ERROR: Failed to release BACnet overrides on stop: {e}")

    async def release_all(self):
        print("Releasing control of AHU cool valve.")
        try:
            await self.bacnet_write(
                AHU_COOL_VALVE_BACNET_ADDR,
                AHU_COOL_VALVE_BACNET_OBJ_ID,
                "null",  # pass a "null" for release
                AHU_COOL_VALVE_WRITE_PRIORITY,
            )
            print("All BACnet overrides have been released.")
        except Exception as e:
            print(f"ERROR: Failed to release AHU cool valve: {e}")


async def main():
    bot = CustomBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
