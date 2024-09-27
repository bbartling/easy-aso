import asyncio
from easy_aso import EasyASO
import random

"""
BACnet write request
"""
BACNET_DEVICE_ADDR = "10.200.200.233"
FAN_CMD_OBJ_ID = "binary-output,1"
VALVE_CMD_OBJ_ID = "analog-output,1"
BACNET_WRITE_PRIORITY = 10

STEP_INTERVAL_SECONDS = 60


class CustomBot(EasyASO):
    async def on_start(self):
        print("CustomBot started!")

    async def on_step(self):

        print("Starting on_step")

        random_bv = random.choice(["active", "inactive"])
        print(f"For a fan command override, doing a {random_bv}...")

        random_float = random.uniform(0.0, 100.0)
        print(f"For a valve percent command override, doing a {random_float}...")

        # BACnet write for fan command
        await self.bacnet_write(
            BACNET_DEVICE_ADDR,
            FAN_CMD_OBJ_ID,
            random_bv,
            BACNET_WRITE_PRIORITY,
        )

        # BACnet write for valve command
        await self.bacnet_write(
            BACNET_DEVICE_ADDR,
            VALVE_CMD_OBJ_ID,
            random_float,
            BACNET_WRITE_PRIORITY,
        )

        print("BACnet step completed.")

        # Wait for the next step
        await asyncio.sleep(STEP_INTERVAL_SECONDS)

    async def on_stop(self):
        print("CustomBot is stopping. Release overrides!")

        # Release fan override
        await self.bacnet_write(
            BACNET_DEVICE_ADDR,
            FAN_CMD_OBJ_ID,
            "null",  # BACnet release is a null string
            BACNET_WRITE_PRIORITY,
        )

        # Release valve override
        await self.bacnet_write(
            BACNET_DEVICE_ADDR,
            VALVE_CMD_OBJ_ID,
            "null",  # BACnet release is a null string
            BACNET_WRITE_PRIORITY,
        )


async def main():
    bot = CustomBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
