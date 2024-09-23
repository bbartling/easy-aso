import asyncio
from easy_aso import EasyASO

"""
$ python load_shed.py --name easy-aso --instance 987654
"""

# BACnet configuration constants
POWER_MTR_BACNET_ADDR = "10.200.200.233"
POWER_MTR_BACNET_OBJ_ID = "analog-input,7"
POWER_THRESHOLD = 120.0  # Fake kW setpoint

AHU_COOL_VALVE_BACNET_ADDR = "10.200.200.233"
AHU_COOL_VALVE_BACNET_OBJ_ID = "analog-output,3"
AHU_COOL_VALVE_WRITE_VALUE = 0.0
AHU_COOL_VALVE_RELEASE_VALUE = "null"
AHU_COOL_VALVE_WRITE_PRIORITY = 10

# Time constants
SLEEP_INTERVAL_SECONDS = 60
DUTY_CYCLE_INTERVAL_SECONDS = 900  # 15 minutes


class LoadShedBot:
    def __init__(self):
        self.last_operation_time = 0

    async def on_start(self):
        """Initialization logic for when the bot starts."""
        print("LoadShedBot started. Monitoring building power consumption.")
        print(f"Power threshold set at {POWER_THRESHOLD} kW.")

    async def check_power(self, app):
        """Check the current power usage of the building."""
        building_power = await app.do_read(POWER_MTR_BACNET_ADDR, POWER_MTR_BACNET_OBJ_ID)
        print(f"Building power is {building_power} kW.")
        return building_power

    async def shed_load_if_needed(self, app, building_power):
        """Apply load-shedding logic based on power usage."""
        current_time = asyncio.get_event_loop().time()
        time_calc = int(DUTY_CYCLE_INTERVAL_SECONDS - (current_time - self.last_operation_time))

        if current_time - self.last_operation_time < DUTY_CYCLE_INTERVAL_SECONDS:
            print(f"Waiting for short cycle prevention timer. Time remaining: {time_calc} seconds.")
        else:
            if building_power > POWER_THRESHOLD:
                print(f"Building power {building_power} exceeds threshold. Lowering setpoint.")
                await app.do_write(AHU_COOL_VALVE_BACNET_ADDR, AHU_COOL_VALVE_BACNET_OBJ_ID,
                                   AHU_COOL_VALVE_WRITE_VALUE, AHU_COOL_VALVE_WRITE_PRIORITY)
                self.last_operation_time = current_time
            elif building_power <= POWER_THRESHOLD:
                print(f"Building power {building_power} is below threshold. Releasing control.")
                await app.do_write(AHU_COOL_VALVE_BACNET_ADDR, AHU_COOL_VALVE_BACNET_OBJ_ID,
                                   AHU_COOL_VALVE_RELEASE_VALUE, AHU_COOL_VALVE_WRITE_PRIORITY)
                self.last_operation_time = current_time

    async def on_step(self, app):
        """Main loop for performing the load-shedding step."""
        building_power = await self.check_power(app)
        await self.shed_load_if_needed(app, building_power)
        print("Load-shedding step complete.")

    async def monitor_building_power(self, app):
        """Continuously monitor power usage and apply load-shedding logic."""
        await self.on_start()
        while True:
            await self.on_step(app)
            await asyncio.sleep(SLEEP_INTERVAL_SECONDS)


async def main():
    load_shed_bot = LoadShedBot()
    await EasyASO().run(load_shed_bot.monitor_building_power)


if __name__ == "__main__":
    asyncio.run(main())
