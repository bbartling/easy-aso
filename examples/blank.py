from easy_aso import EasyASO
import asyncio
from datetime import datetime

"""
run app with custom name and custom BACnet instance ID
python examples/blank.py --name EasyAso --instance 99999

run on a custom UDP port
python examples/blank.py --name EasyAso --instance 99999 --address 10.200.200.223/24:47820
"""


class CustomBot(EasyASO):
    def __init__(self, args=None):
        super().__init__(args)

    async def on_start(self):
        print("ASO: started.")

    async def on_step(self):
        print("ASO: on_step...")
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Current Date and Time: {current_time}")

        # BACnet kill switch
        optimization_status = self.get_optimization_enabled_status()
        print(f"optimization_status: {optimization_status}")

        await asyncio.sleep(5)

    async def on_stop(self):
        print("ASO: stopped.")


async def main():
    bot = CustomBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
