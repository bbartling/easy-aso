import asyncio
import pandas as pd
from datetime import datetime
from easy_aso import EasyASO

# BACnet AHU Info Config
AHU_BACNET_ADDR = "10.200.200.233"

SUP_FAN_SPEED_OBJ_ID = "analog-output,1"
HEAT_VALVE_OBJ_ID = "analog-output,2"
COOL_VALVE_OBJ_ID = "analog-output,3"
MIXING_DAMPER_CMD_OBJ_ID = "analog-output,4"

RET_TEMP_OBJ_ID = "analog-input,4"
MIX_TEMP_OBJ_ID = "analog-input,3"
SUP_TEMP_OBJ_ID = "analog-input,2"
OAT_SENSOR_OBJ_ID = "analog-input,6"
SUP_TEMP_SETPOINT_OBJ_ID = "analog-input,5"

DUCT_STATIC_PRESSURE_OBJ_ID = "analog-input,1"
DUCT_STATIC_PRESSURE_SETPOINT_OBJ_ID = "analog-value,1"

OVERRIDE_PRIORITY = 10
ADJUSTMENT_TIMER_SECONDS = 1200
STEP_INTERVAL_SECONDS = 20
FAULT_THRESHOLD = 5
ECONOMIZER_LOW_TEMP = 55
ECONOMIZER_HIGH_TEMP = 75


class RCxBot(EasyASO):
    def __init__(self, args=None):
        super().__init__(args)
        self.data_cache = (
            []
        )  # Store all readings here as dictionaries for each time step

    async def on_start(self):
        print("RCxBot started. Monitoring AHU for fault detection.")

    async def on_step(self):
        current_time = datetime.now()

        if current_time.weekday() == 1 and current_time.hour == 12:
            print("It's Tuesday noon. Starting RCx process...")

            try:
                oat = await self.bacnet_read(AHU_BACNET_ADDR, OAT_SENSOR_OBJ_ID)
                if oat is None or isinstance(oat, str):
                    raise ValueError(f"Invalid OAT reading: {oat}")
                print(f"Outdoor Air Temperature (OAT): {oat}")
            except Exception as e:
                print(f"ERROR: Failed to read OAT: {e}")
                return

            try:
                if ECONOMIZER_LOW_TEMP <= oat <= ECONOMIZER_HIGH_TEMP:
                    await self.bacnet_write(
                        AHU_BACNET_ADDR,
                        MIXING_DAMPER_CMD_OBJ_ID,
                        100,
                        OVERRIDE_PRIORITY,
                    )
                    print("Economizer mode: Full Economizer (100% outdoor air).")
                else:
                    await self.bacnet_write(
                        AHU_BACNET_ADDR, MIXING_DAMPER_CMD_OBJ_ID, 0, OVERRIDE_PRIORITY
                    )
                    print("Economizer mode: Full Recirculation (0% outdoor air).")
            except Exception as e:
                print(f"ERROR: Failed to write to damper: {e}")

            try:
                await self.bacnet_write(
                    AHU_BACNET_ADDR, HEAT_VALVE_OBJ_ID, 0, OVERRIDE_PRIORITY
                )
                await self.bacnet_write(
                    AHU_BACNET_ADDR, COOL_VALVE_OBJ_ID, 0, OVERRIDE_PRIORITY
                )
                print("AHU heat and cool valves set to 0%.")
            except Exception as e:
                print(f"ERROR: Failed to write to heat/cool valves: {e}")

            print(
                f"Waiting for {ADJUSTMENT_TIMER_SECONDS / 60} minutes for adjustments..."
            )
            await asyncio.sleep(ADJUSTMENT_TIMER_SECONDS)

            for _ in range(15):
                await self.read_multiple_and_cache()
                await asyncio.sleep(STEP_INTERVAL_SECONDS)

            # Calculate rolling averages and check for faults
            await self.calculate_rolling_averages_and_detect_faults()

            # Store data to a Pandas DataFrame for future FDD
            df = pd.DataFrame(self.data_cache)
            print(df.head())  # Display the cached data

            # Release all overrides
            await self.release_all_overrides()

            # Clear caches
            self.clear_caches()

    async def read_multiple_and_cache(self):
        """Perform a BACnet read multiple and cache all readings for future analysis."""
        obj_ids = [
            RET_TEMP_OBJ_ID,
            MIX_TEMP_OBJ_ID,
            SUP_TEMP_OBJ_ID,
            SUP_TEMP_SETPOINT_OBJ_ID,
            COOL_VALVE_OBJ_ID,
            HEAT_VALVE_OBJ_ID,
            SUP_FAN_SPEED_OBJ_ID,
            DUCT_STATIC_PRESSURE_OBJ_ID,
            DUCT_STATIC_PRESSURE_SETPOINT_OBJ_ID,
            MIXING_DAMPER_CMD_OBJ_ID,
        ]

        try:
            readings = await self.bacnet_rpm(AHU_BACNET_ADDR, *obj_ids)
            if readings is None:
                raise ValueError("Failed to read multiple values, returned None")

            # Cache the readings in a dictionary with the current timestamp
            data_point = {
                "timestamp": datetime.now(),
                "return_temp": readings.get(RET_TEMP_OBJ_ID),
                "mix_temp": readings.get(MIX_TEMP_OBJ_ID),
                "supply_temp": readings.get(SUP_TEMP_OBJ_ID),
                "supply_temp_setpoint": readings.get(SUP_TEMP_SETPOINT_OBJ_ID),
                "cool_valve_cmd": readings.get(COOL_VALVE_OBJ_ID),
                "heat_valve_cmd": readings.get(HEAT_VALVE_OBJ_ID),
                "supply_fan_speed": readings.get(SUP_FAN_SPEED_OBJ_ID),
                "duct_static_pressure": readings.get(DUCT_STATIC_PRESSURE_OBJ_ID),
                "duct_static_pressure_setpoint": readings.get(
                    DUCT_STATIC_PRESSURE_SETPOINT_OBJ_ID
                ),
                "mixing_damper_cmd": readings.get(MIXING_DAMPER_CMD_OBJ_ID),
            }

            self.data_cache.append(data_point)  # Append this data point to the cache
            print(f"Cached data at {data_point['timestamp']}: {data_point}")

        except Exception as e:
            print(f"ERROR: Failed to read multiple BACnet points: {e}")

    async def calculate_rolling_averages_and_detect_faults(self):
        """Calculate rolling averages of temperatures and detect faults."""
        try:
            # Extract temperatures for rolling average calculations
            ret_temps = [entry["return_temp"] for entry in self.data_cache]
            mix_temps = [entry["mix_temp"] for entry in self.data_cache]
            sup_temps = [entry["supply_temp"] for entry in self.data_cache]

            avg_ret_temp = sum(ret_temps) / len(ret_temps)
            avg_mix_temp = sum(mix_temps) / len(mix_temps)
            avg_sup_temp = sum(sup_temps) / len(sup_temps)

            print(
                f"5-minute rolling averages - Return: {avg_ret_temp}, Mix: {avg_mix_temp}, Supply: {avg_sup_temp}"
            )

            if abs(avg_ret_temp - avg_mix_temp) > FAULT_THRESHOLD:
                print(
                    "Fault detected: Significant temperature difference between return and mix air."
                )
            else:
                print("No faults detected.")
        except Exception as e:
            print(f"ERROR: Failed to calculate rolling averages or detect faults: {e}")

    async def release_all_overrides(self):
        """Release all BACnet overrides."""
        try:
            await self.bacnet_write(
                AHU_BACNET_ADDR, MIXING_DAMPER_CMD_OBJ_ID, "null", OVERRIDE_PRIORITY
            )
            await self.bacnet_write(
                AHU_BACNET_ADDR, HEAT_VALVE_OBJ_ID, "null", OVERRIDE_PRIORITY
            )
            await self.bacnet_write(
                AHU_BACNET_ADDR, COOL_VALVE_OBJ_ID, "null", OVERRIDE_PRIORITY
            )
            print("All BACnet overrides have been released.")
        except Exception as e:
            print(f"ERROR: Failed to release BACnet overrides: {e}")

    def clear_caches(self):
        """Clear cached data after processing."""
        self.data_cache.clear()
        print("Cache cleared after fault detection and override release.")

    async def on_stop(self):
        """Release all BACnet overrides when stopping."""
        await self.release_all_overrides()


async def main():
    bot = RCxBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
