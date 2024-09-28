from easy_aso import EasyASO
import asyncio
import time

# BACnet configuration
POWER_MTR_BACNET_ADDR = "10.200.200.233"
POWER_MTR_BACNET_OBJ_ID = "analog-input,7"
POWER_THRESHOLD = 120.0  # kW threshold

AHU_COOL_VALVE_BACNET_ADDR = "10.200.200.233"
AHU_COOL_VALVE_BACNET_OBJ_ID = "analog-output,3"
AHU_COOL_VALVE_WRITE_VALUE = 0.0
AHU_COOL_VALVE_RELEASE_VALUE = "null"
AHU_COOL_VALVE_WRITE_PRIORITY = 10

STEP_INTERVAL_SECONDS = 60
STAGE_UP_TIMER_SECONDS = 300
STAGE_DOWN_TIMER_SECONDS = 300


class CustomBot(EasyASO):
    def __init__(self):
        super().__init__()
        self.last_stage_up_time = time.time()  # Initialize with current epoch time
        self.last_stage_down_time = time.time()  # Initialize with current epoch time

    async def on_start(self):
        """Initialization logic for when the bot starts."""
        print("CustomBot started. Monitoring power consumption.")
        # Perform any initial reads
        initial_power = await self.bacnet_read(
            POWER_MTR_BACNET_ADDR, POWER_MTR_BACNET_OBJ_ID
        )
        print(f"Initial power reading: {initial_power} kW")

    async def on_step(self):
        """Main loop for the bot."""
        current_time = (
            time.time()
        )  # Use time.time() to get current real-world time in seconds
        power_reading = await self.bacnet_read(
            POWER_MTR_BACNET_ADDR, POWER_MTR_BACNET_OBJ_ID
        )
        print(f"Current power reading: {power_reading} kW")

        # Get and print the optimization enabled status
        optimization_status = self.get_optimization_enabled_status()
        print(f"Optimization Enabled Status: {optimization_status}")

        # If optimization is not enabled, release all BACnet overrides
        if not optimization_status:
            print("Optimization disabled, releasing all BACnet overrides.")
            await self.release_all()
        else:
            await self.handle_stage_up_logic(current_time, power_reading)
            await self.handle_stage_down_logic(current_time, power_reading)

        await asyncio.sleep(STEP_INTERVAL_SECONDS)

    async def handle_stage_up_logic(self, current_time, power_reading):
        """Handles the logic for stage-up when power exceeds the threshold."""
        stage_up_elapsed = current_time - self.last_stage_up_time
        print(f"Stage Up Timer: {stage_up_elapsed:.2f} seconds elapsed")

        if power_reading > POWER_THRESHOLD:
            if stage_up_elapsed >= STAGE_UP_TIMER_SECONDS:
                print(f"Power {power_reading} exceeds threshold.")
                print(f"Lowering AHU cool valve.")
                await self.bacnet_write(
                    AHU_COOL_VALVE_BACNET_ADDR,
                    AHU_COOL_VALVE_BACNET_OBJ_ID,
                    AHU_COOL_VALVE_WRITE_VALUE,
                    AHU_COOL_VALVE_WRITE_PRIORITY,
                )
                self.last_stage_up_time = current_time  # Update last stage-up time
            else:
                time_remaining = int(STAGE_UP_TIMER_SECONDS - stage_up_elapsed)
                print(f"Waiting for stage up timer.")
                print(f"Time remaining: {time_remaining} seconds.")

    async def handle_stage_down_logic(self, current_time, power_reading):
        """Handles the logic for stage-down when power falls below the threshold."""
        stage_down_elapsed = current_time - self.last_stage_down_time
        print(f"Stage Down Timer: {stage_down_elapsed:.2f} seconds elapsed")

        if power_reading <= POWER_THRESHOLD:
            if stage_down_elapsed >= STAGE_DOWN_TIMER_SECONDS:
                print(f"Power {power_reading} is below threshold.")
                print(f"Releasing control of AHU cool valve.")
                await self.bacnet_write(
                    AHU_COOL_VALVE_BACNET_ADDR,
                    AHU_COOL_VALVE_BACNET_OBJ_ID,
                    AHU_COOL_VALVE_RELEASE_VALUE,
                    AHU_COOL_VALVE_WRITE_PRIORITY,
                )
                self.last_stage_down_time = current_time  # Update last stage-down time
            else:
                time_remaining = int(STAGE_DOWN_TIMER_SECONDS - stage_down_elapsed)
                print(f"Waiting for stage down timer.")
                print(f"Time remaining: {time_remaining} seconds.")

    async def on_stop(self):
        """Clean-up logic when the bot stops."""
        print("on_stop called... Releasing all BACnet overrides.")
        await self.release_all()

    async def release_all(self):
        """
        Releases all BACnet overrides by writing 'null' to the relevant BACnet objects.
        """
        print("Releasing control of AHU cool valve.")
        await self.bacnet_write(
            AHU_COOL_VALVE_BACNET_ADDR,
            AHU_COOL_VALVE_BACNET_OBJ_ID,
            AHU_COOL_VALVE_RELEASE_VALUE,
            AHU_COOL_VALVE_WRITE_PRIORITY,
        )
        print("All BACnet overrides have been released.")


async def main():
    bot = CustomBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
