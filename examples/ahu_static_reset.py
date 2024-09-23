import asyncio
from easy_aso import EasyASO

# BACnet constants
AHU_IP = "192.168.0.103"
FAN_SPEED_BACNET_OBJ_ID = "analog-input,4"  # Fan speed object ID

# VAV addresses
VAV_ADDRESSES = [
    "100:1", "100:2", "100:3", "100:4", "100:5"
]

# Object IDs for VAVs
DAMPER_POSITION_OBJ_ID = "analog-input,1"
AIRFLOW_OBJ_ID = "analog-input,2"
AIRFLOW_SETPOINT_OBJ_ID = "analog-input,3"

# Static pressure control
SP0 = 1.5  # Initial static pressure setpoint
SPmin = 0.5  # Minimum static pressure
SPmax = 3.0  # Maximum static pressure
SPtrim = -0.1  # Pressure decrease when no reset requests
SPres = 0.2  # Pressure increase per reset request
SPres_max = 1.0  # Maximum allowable pressure increase
I = 1  # Number of top dampers to ignore
SLEEP_INTERVAL_SECONDS = 60
FAN_MIN_SPEED = 15.0  # Minimum fan speed to consider fan "running"


class AHUBot(EasyASO):
    def __init__(self):
        super().__init__()
        self.current_sp = SP0
        self.total_pressure_increase = 0

    async def on_start(self):
        print("AHU Bot started! Initial static pressure setpoint is ", self.current_sp)

    async def on_step(self):
        fan_running = await self.check_fan_running()

        if fan_running:
            print("Fan is running. Proceeding with pressure control.")
            vav_data = await self.read_vav_data()
            await self.adjust_static_pressure(vav_data)
        else:
            print("Fan is not running. Skipping pressure control this step.")

        await asyncio.sleep(SLEEP_INTERVAL_SECONDS)

    async def check_fan_running(self):
        fan_speed = await self.do_read(AHU_IP, FAN_SPEED_BACNET_OBJ_ID)
        return fan_speed > FAN_MIN_SPEED

    async def read_vav_data(self):
        vav_data = []
        for address in VAV_ADDRESSES:
            damper_position = await self.do_read(address, DAMPER_POSITION_OBJ_ID)
            airflow = await self.do_read(address, AIRFLOW_OBJ_ID)
            airflow_setpoint = await self.do_read(address, AIRFLOW_SETPOINT_OBJ_ID)
            vav_data.append((damper_position, airflow, airflow_setpoint))
        return vav_data

    async def adjust_static_pressure(self, vav_data):
        total_reset_requests = 0
        vav_data.sort(reverse=True, key=lambda x: x[0])  # Sort by damper position

        vav_data = vav_data[I:]  # Ignore top I VAVs

        for damper_position, airflow, airflow_setpoint in vav_data:
            if airflow_setpoint > 0 and damper_position > 95:
                if airflow < 0.5 * airflow_setpoint:
                    total_reset_requests += 3
                elif airflow < 0.7 * airflow_setpoint:
                    total_reset_requests += 2
                else:
                    total_reset_requests += 1

        if total_reset_requests > 0:
            if self.total_pressure_increase < SPres_max:
                pressure_increase = min(SPres, SPres_max - self.total_pressure_increase)
                self.current_sp = min(self.current_sp + pressure_increase, SPmax)
                self.total_pressure_increase += pressure_increase
                print(f"Pressure increased to {self.current_sp}")
            else:
                print(f"Maximum pressure increase ({SPres_max}) reached.")
        else:
            self.current_sp = max(self.current_sp + SPtrim, SPmin)
            print(f"Pressure trimmed to {self.current_sp}")

        await self.do_write(AHU_IP, "analog-value,10", self.current_sp, 16)


async def main():
    bot = AHUBot()
    await bot.run(bot.on_step)


if __name__ == "__main__":
    asyncio.run(main())
