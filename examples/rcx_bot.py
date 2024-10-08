import asyncio
from datetime import datetime, timedelta
from easy_aso import EasyASO

# BACnet Configuration
AHU_DAMPER_ADDR = "10.200.200.233"
AHU_DAMPER_OBJ_ID = "analog-output,1"  # Example BACnet object ID for AHU damper
HEAT_VALVE_OBJ_ID = "analog-output,2"  # Heat valve
COOL_VALVE_OBJ_ID = "analog-output,3"  # Cool valve
RET_TEMP_OBJ_ID = "analog-input,1"  # Return air temp sensor
MIX_TEMP_OBJ_ID = "analog-input,2"  # Mix air temp sensor
SUP_TEMP_OBJ_ID = "analog-input,3"  # Supply air temp sensor

OVERRIDE_PRIORITY = 10
ADJUSTMENT_TIMER_SECONDS = 1200  # 20 minutes
STEP_INTERVAL_SECONDS = 20
FAULT_THRESHOLD = 5  # Threshold for significant temperature difference


class RCxBot(EasyASO):
    def __init__(self, args=None):
        super().__init__(args)
        self.rolling_average_ret_temp = []
        self.rolling_average_mix_temp = []
        self.rolling_average_sup_temp = []

    async def on_start(self):
        print("RCxBot started. Monitoring AHU for fault detection.")

    async def on_step(self):
        current_time = datetime.now()

        # Check if it's Tuesday at noon
        if current_time.weekday() == 1 and current_time.hour == 12:
            print("It's Tuesday noon. Starting RCx process...")

            # Override AHU dampers and valves to 0%
            await self.bacnet_write(
                AHU_DAMPER_ADDR, AHU_DAMPER_OBJ_ID, 0, OVERRIDE_PRIORITY
            )
            await self.bacnet_write(
                AHU_DAMPER_ADDR, HEAT_VALVE_OBJ_ID, 0, OVERRIDE_PRIORITY
            )
            await self.bacnet_write(
                AHU_DAMPER_ADDR, COOL_VALVE_OBJ_ID, 0, OVERRIDE_PRIORITY
            )
            print("AHU dampers, heat, and cool valves set to 0% (full recirculation).")

            # Wait for adjustment period
            print(
                f"Waiting for {ADJUSTMENT_TIMER_SECONDS / 60} minutes for adjustments..."
            )
            await asyncio.sleep(ADJUSTMENT_TIMER_SECONDS)

            # Start fault detection for 5-minute intervals
            for _ in range(15):  # 15 steps of 20 seconds for 5 minutes
                await self.read_temperatures_and_add_to_average()
                await asyncio.sleep(STEP_INTERVAL_SECONDS)

            # Calculate rolling averages and check for faults
            await self.calculate_rolling_averages_and_detect_faults()

            # Release all overrides
            await self.release_all_overrides()

    async def read_temperatures_and_add_to_average(self):
        """Read return, mix, and supply air temperatures and add to rolling average lists."""
        ret_temp = await self.bacnet_read(AHU_DAMPER_ADDR, RET_TEMP_OBJ_ID)
        mix_temp = await self.bacnet_read(AHU_DAMPER_ADDR, MIX_TEMP_OBJ_ID)
        sup_temp = await self.bacnet_read(AHU_DAMPER_ADDR, SUP_TEMP_OBJ_ID)

        self.rolling_average_ret_temp.append(ret_temp)
        self.rolling_average_mix_temp.append(mix_temp)
        self.rolling_average_sup_temp.append(sup_temp)

        print(
            f"Read temperatures - Return: {ret_temp}, Mix: {mix_temp}, Supply: {sup_temp}"
        )

    async def calculate_rolling_averages_and_detect_faults(self):
        """Calculate rolling averages of temperatures and detect faults."""
        avg_ret_temp = sum(self.rolling_average_ret_temp) / len(
            self.rolling_average_ret_temp
        )
        avg_mix_temp = sum(self.rolling_average_mix_temp) / len(
            self.rolling_average_mix_temp
        )
        avg_sup_temp = sum(self.rolling_average_sup_temp) / len(
            self.rolling_average_sup_temp
        )

        print(
            f"5-minute rolling averages - Return: {avg_ret_temp}, Mix: {avg_mix_temp}, Supply: {avg_sup_temp}"
        )

        # Fault detection: Significant temperature difference between return and mix air
        if abs(avg_ret_temp - avg_mix_temp) > FAULT_THRESHOLD:
            print(
                "Fault detected: Significant temperature difference between return and mix air."
            )
        else:
            print("No faults detected.")

    async def release_all_overrides(self):
        """Release all BACnet overrides."""
        await self.bacnet_write(
            AHU_DAMPER_ADDR, AHU_DAMPER_OBJ_ID, "null", OVERRIDE_PRIORITY
        )
        await self.bacnet_write(
            AHU_DAMPER_ADDR, HEAT_VALVE_OBJ_ID, "null", OVERRIDE_PRIORITY
        )
        await self.bacnet_write(
            AHU_DAMPER_ADDR, COOL_VALVE_OBJ_ID, "null", OVERRIDE_PRIORITY
        )
        print("All BACnet overrides have been released.")

    async def on_stop(self):
        """Release all BACnet overrides when stopping."""
        await self.release_all_overrides()


async def main():
    bot = RCxBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
