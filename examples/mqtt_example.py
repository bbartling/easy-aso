from easy_aso import EasyASO
import asyncio
from datetime import datetime
import paho.mqtt.client as mqtt
import random

'''
run app with custom name and custom BACnet instance ID
python examples/mqtt_example.py --name EasyAso --instance 99999

run on a custom UDP port
python examples/mqtt_example.py --name EasyAso --instance 99999 --address 10.200.200.223/24:47820
'''

class CustomBot(EasyASO):
    def __init__(self, args=None):
        super().__init__(args)
        self.mqtt_client = None
        self.broker_address = "test.mosquitto.org"
        self.port = 1883
        self.topic = "test/sensor/temperature"

    async def on_start(self):
        print("ASO: started.")
        # Initialize MQTT client
        self.mqtt_client = mqtt.Client("FakeSensorPublisher")
        self.mqtt_client.connect(self.broker_address, port=self.port)
        print(f"Connected to MQTT broker at {self.broker_address}")

    async def on_step(self):
        print("ASO: on_step...")
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Current Date and Time: {current_time}")

        # BACnet kill switch
        optimization_status = self.get_optimization_enabled_status()
        print(f"optimization_status: {optimization_status}")

        # Publish a fake sensor reading to MQTT
        temperature = round(random.uniform(20.0, 25.0), 2)
        self.mqtt_client.publish(self.topic, f"Temperature: {temperature} °C")
        print(f"Published: Temperature: {temperature} °C to topic {self.topic}")

        # Sleep for 5 seconds between steps
        await asyncio.sleep(5)

    async def on_stop(self):
        print("ASO: stopped.")
        if self.mqtt_client:
            self.mqtt_client.disconnect()
            print("Disconnected from MQTT broker.")

async def main():
    bot = CustomBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
