import asyncio
from easy_aso import EasyASO

RPM_INTERVAL_SECONDS = 60  # Interval in seconds


class RPMBot(EasyASO):
    async def on_start(self):
        print("RPMBot started! Reading properties periodically.")

    async def on_step(self):
        """
        Periodically read multiple properties from a BACnet device.
        """
        rpm_address = "10.200.200.233"  # BACnet device address
        obj_props = [
            "analog-input,1", "present-value",
            "analog-input,2", "present-value",
        ]

        print("Starting RPM read...")
        rpm_results = await self.do_rpm(rpm_address, *obj_props)

        if rpm_results:
            for result in rpm_results:
                obj_type, obj_instance = result['object_identifier']
                prop_id = result['property_identifier']
                value = result['value']

                # Construct and print the formatted string
                print(f'"{obj_type},{obj_instance}", "{prop_id}", {value}"')

        await asyncio.sleep(RPM_INTERVAL_SECONDS)


async def main():
    bot = RPMBot()
    await bot.run(bot.on_step)


if __name__ == "__main__":
    asyncio.run(main())
