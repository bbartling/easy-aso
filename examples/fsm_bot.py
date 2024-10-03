import asyncio
import random
import time
from easy_aso import EasyASO

# BACnet constants
OUTSIDE_AIR_SENSOR_ADDR = "10.200.200.1"
OUTSIDE_AIR_TEMP_OBJ_ID = "analog-input,1"

BUILDING_POWER_SENSOR_ADDR = "10.200.200.233"
BUILDING_POWER_OBJ_ID = "analog-input,7"
POWER_THRESHOLD = 500  # kW demand threshold to manage

HEAT_PUMP_ADDRESSES = [
    {"id": 1, "address": "10.200.200.50", "obj_id": "analog-output,1", "kW": 5},
    {"id": 2, "address": "10.200.200.51", "obj_id": "analog-output,1", "kW": 8},
]

STEP_INTERVAL_SECONDS = 60
STAGE_UP_TIMER_SECONDS = 300
STAGE_DOWN_TIMER_SECONDS = 300


class HeatPumpManager(EasyASO):
    def __init__(self):
        super().__init__()
        self.heat_pumps = HEAT_PUMP_ADDRESSES
        self.current_load = 0
        self.load_threshold = POWER_THRESHOLD
        self.outside_air_temp = 0

        self.last_stage_up_time = time.time()
        self.last_stage_down_time = time.time()

    async def on_start(self):
        """Initialize the bot and prepare for operations."""
        print("HeatPumpManager started. Monitoring building load and managing heat pumps.")
        await asyncio.sleep(0.1)

    async def on_step(self):
        """Runs in each iteration to monitor and manage the load."""
        current_time = time.time()

        # 3 AM check for load shifting
        if time.localtime().tm_hour == 3:
            print("3 AM check triggered!")
            await self.prepare_load_shift()

        # Monitor the building's power load
        await self.monitor_kW_load(current_time)

        await asyncio.sleep(STEP_INTERVAL_SECONDS)

    async def prepare_load_shift(self):
        """Handles the logic at 3 AM to determine if load shifting is necessary."""
        print("Reading outside air temperature...")
        self.outside_air_temp = await self.bacnet_read(OUTSIDE_AIR_SENSOR_ADDR, OUTSIDE_AIR_TEMP_OBJ_ID)
        print(f"Outside air temperature: {self.outside_air_temp}C")

        # Predict kW based on outside temperature
        predicted_kw = self.predict_kW_from_temp(self.outside_air_temp)
        print(f"Predicted kW at startup: {predicted_kw} kW")

        if predicted_kw > self.load_threshold:
            await self.start_load_shift(predicted_kw)

    async def start_load_shift(self, predicted_kw):
        """Shifts heat pumps to prevent peak demand based on the predicted kW."""
        print("Load shifting required. Managing heat pumps...")

        current_load = 0
        pumps_to_activate = []

        # Sort heat pumps by their zone temperature (simulate lower temperature first)
        sorted_heat_pumps = sorted(self.heat_pumps, key=lambda hp: random.uniform(18, 25))

        # Activate the coldest heat pumps first, until reaching the threshold
        for heat_pump in sorted_heat_pumps:
            if current_load + heat_pump["kW"] < self.load_threshold:
                pumps_to_activate.append(heat_pump)
                current_load += heat_pump["kW"]

        # Activate the selected pumps
        await self.activate_heat_pumps(pumps_to_activate)

    async def monitor_kW_load(self, current_time):
        """Monitors the building kW and adjusts heat pump activity."""
        building_load = await self.bacnet_read(BUILDING_POWER_SENSOR_ADDR, BUILDING_POWER_OBJ_ID)
        print(f"Current building load: {building_load} kW")

        if building_load > self.load_threshold:
            print("Load exceeded threshold. Disabling heat pumps...")
            await self.disable_one_heat_pump()

        elif building_load < self.load_threshold - 50:
            print("Load below threshold. Enabling more heat pumps...")
            await self.enable_one_heat_pump()

    async def activate_heat_pumps(self, pumps_to_activate):
        """Activate selected heat pumps."""
        for pump in pumps_to_activate:
            print(f"Activating Heat Pump {pump['id']} at address {pump['address']}")
            await self.bacnet_write(pump["address"], pump["obj_id"], 1)  # Enable the pump

    async def disable_one_heat_pump(self):
        """Disables one heat pump to reduce load."""
        for pump in self.heat_pumps:
            if pump.get("enabled", False):
                print(f"Disabling Heat Pump {pump['id']}")
                await self.bacnet_write(pump["address"], pump["obj_id"], "null")  # Disable the pump
                pump["enabled"] = False
                break

    async def enable_one_heat_pump(self):
        """Enables one heat pump to increase heating."""
        for pump in self.heat_pumps:
            if not pump.get("enabled", False):
                print(f"Enabling Heat Pump {pump['id']}")
                await self.bacnet_write(pump["address"], pump["obj_id"], 1)  # Enable the pump
                pump["enabled"] = True
                break

    def predict_kW_from_temp(self, outside_temp):
        """Predicts kW based on a simple linear regression of outside temperature."""
        slope = -3  # Example slope
        intercept = 500  # Example intercept
        return slope * outside_temp + intercept

    async def on_stop(self):
        """Handles stopping of the bot and releasing all overrides."""
        print("Releasing all heat pump overrides...")
        for pump in self.heat_pumps:
            await self.bacnet_write(pump["address"], pump["obj_id"], "null")  # Release the pump


async def main():
    manager = HeatPumpManager()
    await manager.run()

if __name__ == "__main__":
    asyncio.run(main())
