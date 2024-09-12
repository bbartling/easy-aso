import asyncio
import re
from typing import Callable, List, Any, Optional, Tuple

from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.app import Application
from bacpypes3.local.binary import BinaryValueObject
from bacpypes3.local.cmd import Commandable
from bacpypes3.pdu import Address
from bacpypes3.object import ObjectIdentifier
from bacpypes3.primitivedata import Null
from bacpypes3.constructeddata import AnyAtomic
from bacpypes3.apdu import (
    ErrorRejectAbortNack,
    PropertyReference,
    PropertyIdentifier,
    ErrorType,
)



# Interval in seconds for server updates
INTERVAL = 1.0

# A regex for parsing property identifier strings
property_index_re = re.compile(r"([a-zA-Z\-]+)(\[(\d+)\])?")

# A list to hold command history (for demonstration purposes)
command_history = []


class CommandableBinaryValueObject(Commandable, BinaryValueObject):
    """
    Commandable Binary Value Object
    """


class EasyASO:
    def __init__(self, args=None):
        # Parse arguments
        self.args = args or SimpleArgumentParser().parse_args()

        print(f"Arguments: {self.args}")

        # Create a commandable binary value object
        self.optimization_enabled_bv = CommandableBinaryValueObject(
            objectIdentifier=("binaryValue", 1),
            objectName="optimization-enabled",
            presentValue="active",
            statusFlags=[0, 0, 0, 0],
            description="Commandable binary value object",
        )
        print(f"Commandable Binary Value Object initialized: {self.optimization_enabled_bv}")

    async def create_application(self):
        # Create an application instance and add objects
        self.app = Application.from_args(self.args)
        self.app.add_object(self.optimization_enabled_bv)
        print("Application and objects created and added.")

    async def update_server(self):
        """
        Simulates BACnet server updates on a fixed interval (e.g., every 1 second).
        """
        while True:
            # Update the server logic here (e.g., handling updates to BACnet objects)
            print("Updating BACnet server...")
            await asyncio.sleep(INTERVAL)  # Wait for 1 second before next update

    def parse_property_identifier(self, property_identifier):
        # BACnet writes processess
        # Regular expression for 'property[index]' matching
        property_index_re = re.compile(r"^([A-Za-z-]+)(?:\[([0-9]+)\])?$")

        # Match the property identifier
        property_index_match = property_index_re.match(property_identifier)
        if not property_index_match:
            raise ValueError(" property specification incorrect")

        property_identifier, property_array_index = property_index_match.groups()
        if property_array_index is not None:
            property_array_index = int(property_array_index)

        return property_identifier, property_array_index

    async def do_read(
        self,
        address: Address,
        object_identifier: ObjectIdentifier,
        property_identifier: str,
        property_array_index=None,  # Set the default value to None
    ) -> Optional[Any]:
        """
        Reads a property from a BACnet object and returns the value directly.
        """

        try:
            # Read the property value
            property_value = await self.app.read_property(
                address, object_identifier, property_identifier, property_array_index
            )
            print(f"Property value: {property_value}")

        except ErrorRejectAbortNack as err:
            print(f"Error while reading property: {err}")
            return None

        # If the value is an atomic type, extract the value
        if isinstance(property_value, AnyAtomic):
            property_value = property_value.get_value()

        return property_value



    async def do_write(
        self,
        address: Address,
        object_identifier: ObjectIdentifier,
        property_identifier: str,
        value: str,
        priority: int = -1,
    ) -> None:
    
        property_identifier, property_array_index = self.parse_property_identifier(
        property_identifier
        )

        # Convert array index to integer if it exists
        if property_array_index is not None:
            property_array_index = int(property_array_index)

        # Handle 'null' values
        if value == "null":
            if priority is None:
                raise ValueError("null can only be used for overrides")
            value = Null(())

        try:
            # Write the property value
            response = await self.app.write_property(
                address,
                object_identifier,
                property_identifier,
                value,
                property_array_index,
                priority,
            )
            print(f"Write successful. Response: {response}")
            assert response is None

        except ErrorRejectAbortNack as err:
            print(f"Error while writing property: {err}")

    async def run(self):
        """
        Starts the ASO application and begins server updates and other tasks.
        """
        await self.create_application()  # Ensure application is created
        await self.update_server()  # Continuously update the BACnet server
        await asyncio.Future()  # Keep the event loop running
