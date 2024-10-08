import asyncio
import signal
from abc import ABC, abstractmethod
from typing import List
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier, Null
from bacpypes3.apdu import (
    ErrorRejectAbortNack,
    PropertyReference,
    PropertyIdentifier,
    ErrorType,
)
from bacpypes3.constructeddata import AnyAtomic
from bacpypes3.app import Application
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.local.cmd import Commandable
from bacpypes3.local.binary import BinaryValueObject
from bacpypes3.vendor import get_vendor_info


class CommandableBinaryValueObject(Commandable, BinaryValueObject):
    """
    Commandable Binary Value Object
    """


class EasyASO(ABC):
    def __init__(self, args=None):
        # Parse arguments
        parser = SimpleArgumentParser()
        parser.add_argument(
            "--no-bacnet-server",
            action="store_true",
            help="Disable the BACnet server functionality",
        )
        self.args = args or parser.parse_args()  # Parse args if not provided
        self.stop_event = asyncio.Event()  # Used to handle stop signal
        self._stop_handler_called = False  # Flag to prevent multiple calls

        # Set the flag for no BACnet server mode
        self.no_bacnet_server = self.args.no_bacnet_server
        print(f"INFO: Arguments: {self.args}")

        # Create a commandable binary value object
        self.optimization_enabled_bv = CommandableBinaryValueObject(
            objectIdentifier=("binaryValue", 1),
            objectName="optimization-enabled",
            presentValue="active",
            statusFlags=[0, 0, 0, 0],
            description="Commandable binary value object",
        )
        print(
            "INFO: Commandable Binary Value Object initialized: ",
            f"{self.optimization_enabled_bv}",
        )

    @abstractmethod
    async def on_start(self):
        """Abstract method that must be implemented by subclasses for start logic"""
        pass

    @abstractmethod
    async def on_step(self):
        """Abstract method that must be implemented by subclasses for step logic"""
        pass

    @abstractmethod
    async def on_stop(self):
        """Abstract method that must be implemented by subclasses for stop logic"""
        pass

    def get_optimization_enabled_status(self):
        """
        Getter method to return the optimization enabled status as a boolean.
        """
        return bool(self.optimization_enabled_bv.presentValue)

    async def create_application(self):
        # Create an application instance and add the commandable binary value object
        self.app = Application.from_args(self.args)
        if not self.args.no_bacnet_server:
            self.app.add_object(self.optimization_enabled_bv)
            print("INFO: Application and BACnet server objects created and added.")
        else:
            print("INFO: Application is created without BACnet server objects.")

    async def update_server(self):
        """
        Simulates server updates on a 1-second interval.
        """
        while True:
            await asyncio.sleep(1)

    async def run_lifecycle(self):
        """Runs the on_start, on_step, on_stop lifecycle."""
        try:
            await self.on_start()
            while not self.stop_event.is_set():
                await self.on_step()
        except asyncio.CancelledError:
            print("INFO: run_lifecycle task cancelled.")
        finally:
            await self.on_stop()

    async def stop_handler(self):
        """Stop handler triggered by signals."""
        if self._stop_handler_called:
            return  # Prevent multiple calls
        self._stop_handler_called = True
        print("Stop handler triggered.")
        self.stop_event.set()
        await self.on_stop()

        # Cancel all tasks except the current one
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()

    async def run(self):
        """
        Starts the EasyASO application, runs the lifecycle (on_start, on_step, on_stop), and handles signals.
        """
        # Set up signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(
                sig, lambda sig=sig: asyncio.create_task(self.stop_handler())
            )

        # Create the application and start the lifecycle
        await self.create_application()
        main_task = asyncio.gather(
            self.update_server(),  # Simulates BACnet server or regular updates
            self.run_lifecycle(),  # Handles the lifecycle internally
        )

        try:
            await main_task
        except asyncio.CancelledError:
            print("INFO: Main tasks cancelled.")
        finally:
            # Clean up: Remove signal handlers
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(sig)
            # Ensure on_stop is called
            if not self._stop_handler_called:
                await self.on_stop()

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

    async def bacnet_rpm(
        self,
        address: Address,
        *args: str,
    ):
        """
        Read Property Multiple (RPM) method to read multiple BACnet properties.

        This method uses vendor information to retrieve a list of dictionaries with
        object identifiers, property identifiers, and either the value or an error message.

        Note:
        - Simple read requests and responses typically don't require segmentation.
        - These services are required if the server supports segmentation or not.
        - The device information cache contains:
        - Vendor identifier (to resolve custom type names),
        - Protocol services supported (to check if RPM and other services are available),
        - Maximum APDU size (to determine if the device can handle the request).
        """
        print(f"Received arguments for RPM: {args}")
        args_list: List[str] = list(args)

        # Convert address string to BACnet Address object
        address_obj = self._convert_to_address(address)

        # Get device info from cache
        device_info = await self.app.device_info_cache.get_device_info(address_obj)

        # Look up vendor information
        vendor_info = get_vendor_info(
            device_info.vendor_identifier if device_info else 0
        )

        parameter_list = []
        while args_list:
            # Translate the object identifier using vendor information
            obj_id_str = args_list.pop(0)
            object_identifier = vendor_info.object_identifier(obj_id_str)
            object_class = vendor_info.get_object_class(object_identifier[0])

            if not object_class:
                print(f"ERROR: Unrecognized object type: {object_identifier}")
                return [{"error": f"Unrecognized object type: {object_identifier}"}]

            # Save this object identifier as a parameter
            parameter_list.append(object_identifier)

            property_reference_list = []
            while args_list:
                # Parse the property reference using vendor info
                property_reference = PropertyReference(
                    propertyIdentifier=args_list.pop(0),
                    vendor_info=vendor_info,
                )
                print(f"INFO: Property reference: {property_reference}")

                # Check if the property is known
                if property_reference.propertyIdentifier not in (
                    PropertyIdentifier.all,
                    PropertyIdentifier.required,
                    PropertyIdentifier.optional,
                ):
                    property_type = object_class.get_property_type(
                        property_reference.propertyIdentifier
                    )
                    print(f"INFO: Property type: {property_type}")

                    if not property_type:
                        print(
                            f"ERROR: Unrecognized property: {property_reference.propertyIdentifier}"
                        )
                        return [
                            {
                                "error": f"Unrecognized property: {property_reference.propertyIdentifier}"
                            }
                        ]

                # Save this property reference as a parameter
                property_reference_list.append(property_reference)

                # Break if the next thing is an object identifier
                if args_list and (":" in args_list[0] or "," in args_list[0]):
                    break

            # Save the property reference list as a parameter
            parameter_list.append(property_reference_list)

        if not parameter_list:
            print("ERROR: Object identifier expected.")
            return [{"error": "Object identifier expected."}]

        try:
            # Perform the read property multiple operation
            response = await self.app.read_property_multiple(
                address_obj, parameter_list
            )
        except ErrorRejectAbortNack as err:
            print(f"ERROR: during RPM: {err}")
            return [{"error": f"Error during RPM: {err}"}]

        # Prepare the response with either property values or error messages
        result_list = []
        for (
            object_identifier,
            property_identifier,
            property_array_index,
            property_value,
        ) in response:
            result = {
                "object_identifier": object_identifier,
                "property_identifier": property_identifier,
                "property_array_index": property_array_index,
            }
            if isinstance(property_value, ErrorType):
                result["value"] = (
                    f"Error: {property_value.errorClass}, {property_value.errorCode}"
                )
            else:
                result["value"] = property_value

            result_list.append(result)

        print("INFO: result_list ", result_list)

        return result_list
