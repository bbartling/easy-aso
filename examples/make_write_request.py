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
    def __init__(self):
        super().__init__()
        self.last_release_time = None

    async def on_start(self):
        print("CustomBot started!")
        await asyncio.sleep(0.1)

    async def on_step(self):
        print("Starting on_step")

        optimization_status = self.get_optimization_enabled_status()
        current_time = asyncio.get_event_loop().time()

        # Check optimization status
        if not optimization_status:
            print("Optimization disabled, releasing all BACnet overrides.")
            await self.release_all()

            while not optimization_status:
                if (
                    self.last_release_time is None
                    or (current_time - self.last_release_time) >= 60
                ):
                    print("Releasing all overrides again (60 seconds passed).")
                    await self.release_all()
                    self.last_release_time = current_time

                await asyncio.sleep(60)
                optimization_status = self.get_optimization_enabled_status()

            print("Optimization re-enabled. Resuming normal operation.")
            return

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
        await asyncio.sleep(STEP_INTERVAL_SECONDS)

    async def on_stop(self):
        print("CustomBot is stopping. Releasing all BACnet overrides.")
        await self.release_all()

    async def release_all(self):
        """
        Releases all BACnet overrides by writing 'null' to the fan and valve.
        """
        print("Releasing fan override...")
        await self.bacnet_write(
            BACNET_DEVICE_ADDR,
            FAN_CMD_OBJ_ID,
            "null",  # BACnet release is a null string
            BACNET_WRITE_PRIORITY,
        )

        print("Releasing valve override...")
        await self.bacnet_write(
            BACNET_DEVICE_ADDR,
            VALVE_CMD_OBJ_ID,
            "null",  # BACnet release is a null string
            BACNET_WRITE_PRIORITY,
        )

        print("All BACnet overrides have been released.")


async def main():
    bot = CustomBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
