import asyncio
from easy_aso import EasyASO
import random


BACNET_DEVICE_ADDR = "bacnet-server"

WRITE_A_POINT = "analog-value,2"
READ_AV1_POINT = "analog-value,1"
READ_BV1_POINT = "binary-value,1"

BACNET_WRITE_PRIORITY = 10

STEP_INTERVAL_SECONDS = 2


class CustomBot(EasyASO):
    def __init__(self, args=None):
        super().__init__(args)
        self.last_release_time = None

    async def on_start(self):
        print("CustomBot started!")
        await asyncio.sleep(0.1)

    async def on_step(self):
        print("Starting on_step")

        optimization_status = self.get_optimization_enabled_status()
        current_time = asyncio.get_event_loop().time()

        print(f"Optimization status is {optimization_status}")

        # Check optimization status
        if not optimization_status:
            print("Optimization disabled, releasing all BACnet overrides.")
            await self.release_all()

            while not optimization_status:
                if (
                    self.last_release_time is None
                    or (current_time - self.last_release_time) >= STEP_INTERVAL_SECONDS
                ):
                    print(
                        "Releasing all overrides again (STEP_INTERVAL_SECONDS seconds passed)."
                    )
                    await self.release_all()
                    self.last_release_time = current_time

                await asyncio.sleep(STEP_INTERVAL_SECONDS)
                optimization_status = self.get_optimization_enabled_status()

            print("Optimization re-enabled. Resuming normal operation.")
            return

        av1_pv = await self.bacnet_read(BACNET_DEVICE_ADDR, READ_AV1_POINT)
        print("av1_pv ", av1_pv)

        av2_pv = await self.bacnet_read(BACNET_DEVICE_ADDR, WRITE_A_POINT)
        print("av2_pv ", av2_pv)

        bv1_pv = await self.bacnet_read(BACNET_DEVICE_ADDR, READ_BV1_POINT)
        print("bv1_pv ", bv1_pv)

        random_float = random.uniform(0.0, 100.0)

        # BACnet write for fan command
        await self.bacnet_write(
            BACNET_DEVICE_ADDR,
            WRITE_A_POINT,
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
            WRITE_A_POINT,
            "null",  # BACnet release is a null string
            BACNET_WRITE_PRIORITY,
        )

        print("All BACnet overrides have been released.")


async def main():
    bot = CustomBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
