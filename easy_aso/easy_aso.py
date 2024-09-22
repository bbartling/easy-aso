import asyncio
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier, Null
from bacpypes3.apdu import ErrorRejectAbortNack
from bacpypes3.constructeddata import AnyAtomic
from bacpypes3.app import Application
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.local.cmd import Commandable
from bacpypes3.local.binary import BinaryValueObject

from easy_aso.algorithms.load_shed.load_shed_algorithm import load_shed
from easy_aso.algorithms.ahu_duct_static_reset.ahu_static_reset_algorithm import (
    AHUStaticPressureReset,
)  # Updated import


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
        print(
            f"Commandable Binary Value Object initialized: {self.optimization_enabled_bv}"
        )

    def get_optimization_enabled_status(self):
        """
        Getter method to return the optimization enabled status as a boolean.
        """
        return bool(self.optimization_enabled_bv.presentValue)

    async def create_application(self):
        # Create an application instance and add the commandable binary value object
        self.app = Application.from_args(self.args)
        self.app.add_object(self.optimization_enabled_bv)
        print("Application and objects created and added.")

    async def update_server(self):
        """
        Simulates server updates on a 1-second interval.
        """
        while True:
            await asyncio.sleep(1)

    async def do_read(
        self, address: str, object_identifier: str, property_identifier="present-value"
    ):
        """
        Handles reading from a BACnet object. Uses 'present-value' as default property identifier.
        """
        try:
            address_obj = self._convert_to_address(address)
            object_id_obj = self._convert_to_object_identifier(object_identifier)
            property_value = await self.app.read_property(
                address_obj, object_id_obj, property_identifier
            )

            if isinstance(property_value, AnyAtomic):
                return property_value.get_value()

            return property_value

        except ErrorRejectAbortNack as e:
            print(f"Error reading property: {e}")
            return None
        except TypeError as e:
            print(
                f"Type error while reading property: {e} - Address: {address}, Object ID: {object_identifier}, Property Identifier: {property_identifier}"
            )
            return None
        except Exception as e:
            print(
                f"Unexpected error while reading property: {e} - Address: {address}, Object ID: {object_identifier}, Property Identifier: {property_identifier}"
            )
            return None

    def parse_property_identifier(self, property_identifier):
        # Example parsing logic (modify as needed for your use case)
        if "," in property_identifier:
            prop_id, prop_index = property_identifier.split(",")
            return prop_id.strip(), int(prop_index.strip())
        return property_identifier, None

    async def do_write(
        self,
        address: str,
        object_identifier: str,
        value: any,
        priority: int = -1,
        property_identifier="present-value",
    ):
        """
        Handles writing to a BACnet object. Uses 'present-value' as default property identifier.
        If value is 'null', it triggers a release using Null().
        """
        try:
            address_obj = self._convert_to_address(address)
            object_id_obj = self._convert_to_object_identifier(object_identifier)

            # Parse property identifier and index
            property_identifier, property_array_index = self.parse_property_identifier(
                property_identifier
            )

            # Handle 'null' values for release
            if value == "null":
                if priority is None:
                    raise ValueError(
                        "null can only be used for overrides with a priority"
                    )
                value = Null(())

            # Write the property value
            response = await self.app.write_property(
                address_obj,
                object_id_obj,
                property_identifier,
                value,
                property_array_index,
                priority,
            )
            print(
                f"Write successful. Value: {value}, Priority: {priority}, Response: {response}"
            )

        except ErrorRejectAbortNack as e:
            print(f"Error writing property: {e}")
        except TypeError as e:
            print(f"Type error while writing property: {e} - Value attempted: {value}")
        except Exception as e:
            print(
                f"Unexpected error while writing property: {e} - Value attempted: {value}"
            )

    async def run(self, custom_task):
        """
        Starts the EasyASO application and runs the custom monitoring task.
        """
        await self.create_application()  # Ensure application is created
        await asyncio.gather(
            self.update_server(),  # Runs server updates in the background
            custom_task(self),  # Runs the custom task (e.g., monitoring logic)
        )

    def _convert_to_address(self, address: str) -> Address:
        """
        Convert a string to a BACnet Address object.
        """
        return Address(address)

    def _convert_to_object_identifier(self, obj_id: str) -> ObjectIdentifier:
        """
        Convert a string to a BACnet ObjectIdentifier.
        """
        object_type, instance_number = obj_id.split(",")
        return ObjectIdentifier((object_type.strip(), int(instance_number.strip())))

    async def run_load_shed(self, config_dict):
        """
        Runs the load shedding algorithm with the given configuration.
        """
        await self.run(lambda app: load_shed(app, config_dict))

    async def run_ahu_static_pressure_reset(self, config_dict):
        """
        Runs the AHU Static Pressure Reset algorithm using the refactored class.
        """
        # Create an instance of the AHUStaticPressureReset class
        ahu_reset = AHUStaticPressureReset(config_dict)

        # Run the algorithm
        await self.run(lambda app: ahu_reset.run(app))
