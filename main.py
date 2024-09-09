# main.py
from bacnet_client import BACnetClient
from models import ReadMultiplePropertiesRequest

async def run_bacnet_operations():
    client = BACnetClient()

    async with client.manage_bacnet_service():
        # Example read and write logic
        device_instance = 12345
        object_identifier = "analog-input,2"
        property_identifier = "present-value"
        value = 50.0

        # Perform read
        read_result = await client.read_property(device_instance, object_identifier, property_identifier)
        print(f"Read result: {read_result}")

        # Perform write
        write_result = await client.write_property(device_instance, object_identifier, property_identifier, value)
        print(f"Write result: {write_result}")

        # Perform WhoIs
        who_is_result = await client.perform_who_is(1000, 5000)
        print(f"WhoIs result: {who_is_result}")

        # Perform point discovery
        point_discovery_result = await client.point_discovery(device_instance)
        print(f"Point discovery result: {point_discovery_result}")

        # Perform BACnet read multiple
        read_multiple_requests = [
            ReadMultiplePropertiesRequest(object_identifier="analog-input,1", property_identifier="present-value"),
            ReadMultiplePropertiesRequest(object_identifier="analog-output,2", property_identifier="description")
        ]
        read_multiple_result = await client.read_multiple_properties(device_instance, read_multiple_requests)
        print(f"Read multiple properties result: {read_multiple_result}")

        # Perform WhoIs range
        who_is_range_result = await client.who_is_range(1000, 1500)
        print(f"WhoIs range result: {who_is_range_result}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_bacnet_operations())
