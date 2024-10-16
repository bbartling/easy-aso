import asyncio
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.app import Application
from bacpypes3.local.analog import AnalogValueObject
from bacpypes3.local.binary import BinaryValueObject
from bacpypes3.local.cmd import Commandable
from bacpypes3.object import ObjectIdentifier
from bacpypes3.primitivedata import Null
from bacpypes3.constructeddata import AnyAtomic
from bacpypes3.apdu import ErrorRejectAbortNack
from bacpypes3.pdu import Address


INTERVAL = 1.0  # Interval for printing values
WRITE_TASK_INTERVAL = 2.0  # Interval for writing values to BACnet

# BACnet constants for reading
BACNET_DEVICE_ADDRESS = "bacnet-client"
BACNET_READ_OBJECT_IDENTIFIER = "binary-value,1"
BACNET_READ_PROPERTY_IDENTIFIER = "present-value"

# BACnet constants for writing
BACNET_WRITE_OBJECT_IDENTIFIER = "binary-value,1"
BACNET_WRITE_PROPERTY_IDENTIFIER = "present-value"
BACNET_WRITE_VALUE = 0
BACNET_WRITE_RELEASE_VALUE = "null"
BACNET_WRITE_VALUE_WRITE_PRIORITY = 10


class CommandableAnalogValueObject(Commandable, AnalogValueObject):
    """
    Commandable Analog Value Object
    """


class SampleApplication:
    def __init__(self, args, test_bv, test_av, commandable_analog_value):
        # embed an application
        self.app = Application.from_args(args)

        # extract the kwargs that are special to this application
        self.test_bv = test_bv
        self.app.add_object(test_bv)

        self.test_av = test_av
        self.app.add_object(test_av)

        self.commandable_analog_value = commandable_analog_value
        self.app.add_object(commandable_analog_value)

        self.last_write_val = BACNET_WRITE_VALUE

        print(
            "INFO: Commandable Analog Value Object initialized: ",
            f"{self.commandable_analog_value}",
        )

        # create tasks to periodically print values, read, and write to BACnet
        asyncio.create_task(self.print_values())
        asyncio.create_task(self.bacnet_read_task())
        asyncio.create_task(self.bacnet_write_task())

    async def print_values(self):
        """
        Periodically prints the values of test_bv, test_av, and commandable_analog_value.
        """
        while True:
            print("----------------------------------------")
            print("test_bv: ", self.test_bv.presentValue)
            print("test_av: ", self.test_av.presentValue)
            print("test_cav: ", self.commandable_analog_value.presentValue)
            await asyncio.sleep(
                INTERVAL
            )  # Wait for the specified interval before printing again

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

    def parse_property_identifier(self, property_identifier):
        # Example parsing logic (modify as needed for your use case)
        if "," in property_identifier:
            prop_id, prop_index = property_identifier.split(",")
            return prop_id.strip(), int(prop_index.strip())
        return property_identifier, None

    async def bacnet_read(
        self, address: str, object_identifier: str, property_identifier="present-value"
    ):
        """
        Handles reading from a BACnet object.
        Uses 'present-value' as default property identifier.
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
            print(f"ERROR: reading property: {e}")
            return None
        except TypeError as e:
            print(
                f"ERROR: Type error while reading property: {e} - Address: {address}, "
                f"Object ID: {object_identifier}, Property Identifier: {property_identifier}"
            )
            return None
        except Exception as e:
            print(
                f"ERROR: Unexpected error while reading property: {e} - Address: {address}, "
                f"Object ID: {object_identifier}, Property Identifier: {property_identifier}"
            )
            return None

    async def bacnet_write(
        self,
        address: str,
        object_identifier: str,
        value: any,
        priority: int = -1,
        property_identifier="present-value",
    ):
        """
        Handles writing to a BACnet object.
        Uses 'present-value' as default property identifier.
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
                value = Null(())  # Convert 'null' string to Null object

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
                f"INFO: {address} Write successful, ",
                f"Value: {value}, ",
                f"Priority: {priority}, ",
                f"Response: {response}",
            )

        except ErrorRejectAbortNack as e:
            print(f"ERROR: writing property: {e}")
        except TypeError as e:
            print(
                f"ERROR: Type error while writing property: {e} ",
                f"Value attempted: {value}",
            )
        except Exception as e:
            print(
                f"ERROR: Unexpected error while writing property: {e} ",
                f"Value attempted: {value}",
            )

    async def bacnet_read_task(self):
        """
        Periodically reads a value from the BACnet device and prints it.
        """
        while True:
            property_value = await self.bacnet_read(
                BACNET_DEVICE_ADDRESS,
                BACNET_READ_OBJECT_IDENTIFIER,
                BACNET_READ_PROPERTY_IDENTIFIER,
            )
            print(
                f"BACnet Read - Address: {BACNET_DEVICE_ADDRESS}, Object: {BACNET_READ_OBJECT_IDENTIFIER}, Value: {property_value}"
            )
            await asyncio.sleep(INTERVAL)

    async def bacnet_write_task(self):
        """
        Periodically writes a value to a BACnet object, alternating between writing a value and releasing the override.
        """
        write_value = None

        while True:

            if self.last_write_val == 0:
                write_value = 1
            else:
                write_value = 0

            print(f"Writing Value: {write_value}")
            await self.bacnet_write(
                BACNET_DEVICE_ADDRESS,
                BACNET_WRITE_OBJECT_IDENTIFIER,
                write_value,
                BACNET_WRITE_VALUE_WRITE_PRIORITY,
                BACNET_WRITE_PROPERTY_IDENTIFIER,
            )

            self.last_write_val = write_value

            # Wait for the next write task interval
            await asyncio.sleep(WRITE_TASK_INTERVAL)


async def main():
    parser = SimpleArgumentParser()
    args = parser.parse_args()

    print("args: %r", args)

    # define BACnet objects
    test_av = AnalogValueObject(
        objectIdentifier=("analogValue", 1),
        objectName="av",
        presentValue=0.0,
        statusFlags=[0, 0, 0, 0],
        covIncrement=1.0,
    )
    print("    - test_av: %r", test_av)

    test_bv = BinaryValueObject(
        objectIdentifier=("binaryValue", 1),
        objectName="bv",
        presentValue="inactive",
        statusFlags=[0, 0, 0, 0],
    )
    print("    - test_bv: %r", test_bv)

    # Create an instance of your commandable analog object
    commandable_analog_value = CommandableAnalogValueObject(
        objectIdentifier=("analogValue", 2),
        objectName="commandable-av",
        presentValue=-1.0,
        statusFlags=[0, 0, 0, 0],
        covIncrement=1.0,
        description="Commandable analog value object",
    )

    # instantiate the SampleApplication with the objects
    app = SampleApplication(
        args,
        test_av=test_av,
        test_bv=test_bv,
        commandable_analog_value=commandable_analog_value,
    )

    print("app: %r", app)

    await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Keyboard interrupt")
