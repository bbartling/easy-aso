import asyncio
from easy_aso import EasyASO
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier

address = Address("10.200.200.233")  # Replace with the actual IP address of the device
object_identifier = ObjectIdentifier("analog-value,12")  # Replace with the correct object identifier
property_identifier = "present-value"

async def monitor_building_power(app, interval: int):
    """
    Monitors the building power at a set interval and applies optimization logic if necessary.
    """
    while True:
        # Perform a read operation to get the building power
        building_power = await app.do_read(address, object_identifier, property_identifier)
        print("Building power is ", building_power)

        # Simulate logic: If the building power is greater than 100, override equipment or setpoint
        if building_power and float(building_power) > 100:
            print(f"Building power is {building_power}, exceeding threshold. Lowering setpoint...")
            await app.do_write(address, object_identifier, property_identifier, 72.0, 10)
        else:
            print(f"Building power is {building_power}, no need to override.")

        # Wait for the specified interval before checking again
        await asyncio.sleep(interval)

async def run_easy_aso(interval: int):
    """
    Function to create and run EasyASO instance with periodic monitoring and server updates.
    """
    try:
        app = EasyASO()

        # Ensure the application is created before doing anything else
        await app.create_application()

        # Run both the server update task and the building power monitor concurrently
        await asyncio.gather(
            app.update_server(),  # Server updates every 1 second
            monitor_building_power(app, interval)  # Monitor building power at specified interval
        )

    except KeyboardInterrupt:
        print("ASO application interrupted.")

if __name__ == "__main__":
    # Set the interval in seconds for checking the building power
    INTERVAL = 60  # Example: Check building power every 60 seconds

    # Run the asyncio event loop
    asyncio.run(run_easy_aso(INTERVAL))
