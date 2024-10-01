import asyncio
from easy_aso import EasyASO
from collections import deque
import time
import random  # Assuming we use random for simulating temp and kW readings

# BACnet addresses for building
OAT_BACNET_ADDR = "10.200.200.233"
OAT_BACNET_OBJ_ID = "analog-input,7"  # Outside Air Temp sensor ID

BUILDING_KW_THRESHOLD = 200.0  # Building kW limit for load-shifting
HEAT_PUMPS = [
    {
        "name": "HP1",
        "addr": "10.200.200.231",
        "kw_rate": 5.0,
        "zone_temp": 18.0,
        "enabled": False,
    },
    {
        "name": "HP2",
        "addr": "10.200.200.232",
        "kw_rate": 4.5,
        "zone_temp": 17.5,
        "enabled": False,
    },
    # Add more heat pumps as needed...
]

STEP_INTERVAL_SECONDS = 300  # 5-minute step intervals


class CustomHvacBot(EasyASO):
    def __init__(self):
        super().__init__()
        self.current_state = "INIT"  # Initial FSM state
        self.startup_kw = 0.0  # Estimated kW load for building startup
        self.active_heat_pumps = deque()  # Queue for active heat pumps
        self.next_check_time = None  # Timestamp for next check
        self.selected_heat_pumps = []  # List of heat pumps selected for load-shifting

    async def on_start(self):
        # Custom start logic
        self.next_check_time = (
            self.get_3am_check_time()
        )  # Calculate when 3AM check occurs
        print("CustomHvacBot is starting. Waiting for 3AM check...")

    async def on_step(self):
        current_time = time.time()

        if self.current_state == "INIT":
            await self.init_state()

        elif self.current_state == "PREPARE_LOAD_SHIFT":
            if current_time >= self.next_check_time:
                await self.prepare_load_shift()

        elif self.current_state == "LOAD_SHIFT":
            await self.load_shift_state()

        elif self.current_state == "WAIT":
            await self.wait_state()

        elif self.current_state == "DONE":
            print("Load shift completed successfully. All heat pumps are now enabled.")
            self.current_state = "DONE"

        # Always sleep for the defined step interval
        await asyncio.sleep(STEP_INTERVAL_SECONDS)

    async def on_stop(self):
        print("Stopping HVAC bot. Releasing all heat pumps.")
        await self.release_all_heat_pumps()

    def get_3am_check_time(self):
        """
        Returns the next 3AM time in seconds since epoch.
        """
        now = time.localtime()
        return time.mktime(
            (
                now.tm_year,
                now.tm_mon,
                now.tm_mday,
                3,
                0,
                0,
                now.tm_wday,
                now.tm_yday,
                now.tm_isdst,
            )
        )

    async def init_state(self):
        # Read the current outside air temperature
        oat_temp = await self.bacnet_read(OAT_BACNET_ADDR, OAT_BACNET_OBJ_ID)
        print(f"Current Outside Air Temp: {oat_temp}°C")

        # Prepare for 3AM check, move to next state
        self.current_state = "PREPARE_LOAD_SHIFT"

    async def prepare_load_shift(self):
        # At 3AM, check outside air temp and calculate building startup kW using linear regression
        oat_temp = await self.bacnet_read(OAT_BACNET_ADDR, OAT_BACNET_OBJ_ID)
        self.startup_kw = self.calculate_startup_kw(oat_temp)  # Linear regression model
        print(
            f"Startup kW estimation based on outside air temp ({oat_temp}°C): {self.startup_kw} kW"
        )

        if self.startup_kw > BUILDING_KW_THRESHOLD:
            print(
                f"Estimated startup kW ({self.startup_kw}) exceeds threshold ({BUILDING_KW_THRESHOLD}). Initiating load shift."
            )
            self.select_heat_pumps_for_shift()  # Select heat pumps for load-shifting
            self.current_state = "LOAD_SHIFT"
        else:
            print(f"Startup kW is below threshold. No load-shifting required.")
            self.current_state = "DONE"

    async def load_shift_state(self):
        # Enable the selected heat pumps one by one based on the coldest zones first
        for hp in self.selected_heat_pumps:
            print(
                f"Enabling {hp['name']} (kW: {hp['kw_rate']}, Temp: {hp['zone_temp']}°C)"
            )
            await self.bacnet_write(hp["addr"], "binary-output,1", "active", 10)
            self.active_heat_pumps.append(hp)  # Add to active list
            await asyncio.sleep(1)  # Small delay for safety

        # Move to WAIT state after enabling selected pumps
        self.current_state = "WAIT"

    async def wait_state(self):
        # Monitor kW and ensure it stays under threshold
        current_building_kw = random.uniform(100, 300)  # Simulate building kW reading
        print(f"Current building kW: {current_building_kw} kW")

        if current_building_kw > BUILDING_KW_THRESHOLD:
            print("Building kW exceeded. Disabling one heat pump to reduce load.")
            if self.active_heat_pumps:
                hp = self.active_heat_pumps.pop()
                await self.bacnet_write(hp["addr"], "binary-output,1", "inactive", 10)
                print(f"Disabled {hp['name']} (kW: {hp['kw_rate']}).")
            else:
                print("No more heat pumps to disable.")
        else:
            print("Building kW is within limits. Holding current load.")

        # Continue monitoring for a set period (e.g., 15 minutes)
        await asyncio.sleep(900)  # 15-minute WAIT period before resuming

        # Move back to LOAD_SHIFT to continue bringing pumps online
        if self.active_heat_pumps:
            self.current_state = "LOAD_SHIFT"
        else:
            self.current_state = "DONE"

    def calculate_startup_kw(self, oat_temp):
        """
        Placeholder for linear regression model.
        Adjust based on actual regression logic.
        """
        return oat_temp * 1.5  # Simplified linear regression

    def select_heat_pumps_for_shift(self):
        # Sort heat pumps by zone temperature (coldest first)
        self.selected_heat_pumps = sorted(HEAT_PUMPS, key=lambda x: x["zone_temp"])
        print(f"Selected {len(self.selected_heat_pumps)} heat pumps for load-shifting.")

    async def release_all_heat_pumps(self):
        # Release all active heat pumps
        for hp in self.active_heat_pumps:
            await self.bacnet_write(hp["addr"], "binary-output,1", "inactive", 10)
            print(f"Released {hp['name']} from control.")
        self.active_heat_pumps.clear()


# main.py
async def main():
    bot = CustomHvacBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
