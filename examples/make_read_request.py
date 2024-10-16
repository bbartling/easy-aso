import asyncio
from easy_aso import EasyASO


"""
BACnet read request example
"""

# BACnet MSTP device
# Hardware address 22 MSTP trunk 12
# BACNET_DEVICE_ADDR = "11:21"
# BACNET_OBJ_ID = "analog-input,1019"

BACNET_DEVICE_ADDR = "10.200.200.233"
BACNET_OBJ_ID = "analog-value,1"

STEP_INTERVAL_SECONDS = 10


class CustomBot(EasyASO):
    def __init__(self, args=None):
        super().__init__(args)

    async def on_start(self):
        print("ReadRequest on_start!")

    async def on_step(self):

        print("Starting ReadRequest on_step...")

        # Get and print the optimization enabled status
        optimization_status = self.get_optimization_enabled_status()
        print(f"Optimization Enabled Status: {optimization_status}")

        # VAV box discharge air temp sensor
        sensor_value_pv = await self.bacnet_read(BACNET_DEVICE_ADDR, BACNET_OBJ_ID)
        print(sensor_value_pv)

        await asyncio.sleep(STEP_INTERVAL_SECONDS)

    async def on_stop(self):
        print("ReadRequest on_stop!")


async def main():
    bot = CustomBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
