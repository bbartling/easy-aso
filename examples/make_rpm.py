import asyncio
from easy_aso import EasyASO


"""
BACnet read multiple request
"""
STEP_INTERVAL_SECONDS = 60


class RPMBot(EasyASO):
    async def on_start(self):
        print("RPMBot started! Reading properties periodically.")

    async def on_step(self):
        rpm_address = "10.200.200.233"  # BACnet device address
        obj_props = [
            "analog-input,1",
            "present-value",
            "analog-input,2",
            "present-value",
        ]

        print("Starting RPM read...")
        rpm_results = await self.bacnet_rpm(rpm_address, *obj_props)

        if rpm_results:
            for result in rpm_results:
                obj_type, obj_instance = result["object_identifier"]
                prop_id = result["property_identifier"]
                value = result["value"]

                print(f'"{obj_type},{obj_instance}", "{prop_id}", {value}"')

        await asyncio.sleep(STEP_INTERVAL_SECONDS)

    async def on_stop(self):
        print("RPMBot is stopping. Cleaning up resources...")


async def main():
    bot = RPMBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
