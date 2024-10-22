from easy_aso import EasyASO
import asyncio
import aiomqtt

"""
BACnet read request example with MQTT
pip install aiomqtt

run app with custom name and custom BACnet instance ID
python examples/mqtt_example.py --name EasyAso --instance 99999

run on a custom UDP port with passing in IP address of your device
python examples/mqtt_example.py --name EasyAso --instance 99999 --address 10.200.200.223/24:47820

"""

# BACnet MSTP device example
BACNET_DEVICE_ADDR = "11:21"
BACNET_OBJ_ID = "analog-input,1019"

# MQTT settings
BROKER_ADDRESS = "test.mosquitto.org"
MQTT_TOPIC = "test/sensor/discharge_air_temp"
STEP_INTERVAL_SECONDS = 30


class CustomBot(EasyASO):
    def __init__(self, args=None):
        super().__init__(args)
        self.mqtt_client = None

    async def on_start(self):
        print("ReadRequest on_start!")
        # Initialize MQTT client
        self.mqtt_client = aiomqtt.Client(BROKER_ADDRESS)

    async def on_step(self):
        print("Starting ReadRequest on_step...")

        # Get and print the optimization enabled status
        optimization_status = self.get_optimization_enabled_status()
        print(f"Optimization Enabled Status: {optimization_status}")

        # Perform BACnet read request (VAV box discharge air temp sensor)
        sensor_value_pv = await self.bacnet_read(BACNET_DEVICE_ADDR, BACNET_OBJ_ID)
        print(f"Read BACnet sensor value: {sensor_value_pv}")

        # Publish the sensor value to the MQTT bus
        async with self.mqtt_client as client:
            await client.publish(
                MQTT_TOPIC, payload=f"Discharge Air Temp: {sensor_value_pv}"
            )
            print(f"Published to MQTT: Discharge Air Temp: {sensor_value_pv}")

        await asyncio.sleep(STEP_INTERVAL_SECONDS)

    async def on_stop(self):
        print("ReadRequest on_stop!")


async def main():
    bot = CustomBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
