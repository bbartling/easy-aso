import asyncio
from easy_aso import EasyASO


"""
BACnet read multiple request
"""

RPM_ADDRESS = "10.200.200.233"  # BACnet device address
BACNET_RPM_OBJ = [
    "analog-input,1",
    "present-value",
    "analog-input,2",
    "present-value",
]

STEP_INTERVAL_SECONDS = 60


class RPMBot(EasyASO):
    def __init__(self, args=None):
        super().__init__(args)

    async def on_start(self):
        print("RPMBot started! Reading properties periodically.")

    async def on_step(self):

        print("Starting RPM read...")

        # Get and print the optimization enabled status
        optimization_status = self.get_optimization_enabled_status()
        print(f"Optimization Enabled Status: {optimization_status}")

        rpm_results = await self.bacnet_rpm(RPM_ADDRESS, *BACNET_RPM_OBJ)

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
