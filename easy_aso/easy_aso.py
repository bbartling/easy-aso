import asyncio
from abc import ABC, abstractmethod
from typing import Callable, List, Any, Optional, Tuple

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

    @abstractmethod
    async def on_start(self):
        """Custom start logic that must be implemented by subclasses"""
        pass

    @abstractmethod
    async def on_step(self):
        """Custom step logic that must be implemented by subclasses"""
        pass

    @abstractmethod
    async def on_stop(self):
        """Custom stop logic that must be implemented by subclasses"""
        pass

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

    async def run(self):
        """
        Starts the EasyASO application and runs the custom lifecycle (on_start, on_step, on_stop).
        """
        await self.create_application()  # Ensure application is created

        try:
            await self.on_start()  # Run the custom on_start logic
            while True:
                await self.on_step()  # Continuously run the custom on_step logic
        except KeyboardInterrupt:
            # Handle graceful shutdown on stop signal
            await self.on_stop()  # Run the custom on_stop logic
        finally:
            print("EasyASO shutting down...")

    # BACnet-specific methods (do_read, do_write, etc.) remain the same...

    def _convert_to_address(self, address: str) -> Address:
        """Convert a string to a BACnet Address object."""
        return Address(address)

    def _convert_to_object_identifier(self, obj_id: str) -> ObjectIdentifier:
        """Convert a string to a BACnet ObjectIdentifier."""
        object_type, instance_number = obj_id.split(",")
        return ObjectIdentifier((object_type.strip(), int(instance_number.strip())))

    async def do_read(
        self, address: str, object_identifier: str, property_identifier="present-value"
    ):
        """Handles reading from a BACnet object."""
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
            return {"error": f"Error reading property: {e}"}
        except TypeError as e:
            print(f"Type error while reading property: {e}")
            return {"error": f"Type error while reading property: {e}"}
        except Exception as e:
            print(f"Unexpected error while reading property: {e}")
            return {"error": f"Unexpected error while reading property: {e}"}

    async def do_write(
        self,
        address: str,
        object_identifier: str,
        value: any,
        priority: int = -1,
        property_identifier="present-value",
    ):
        """Handles writing to a BACnet object."""
        try:
            address_obj = self._convert_to_address(address)
            object_id_obj = self._convert_to_object_identifier(object_identifier)

            property_identifier, property_array_index = self.parse_property_identifier(
                property_identifier
            )

            if value == "null":
                if priority is None:
                    raise ValueError(
                        "null can only be used for overrides with a priority"
                    )
                value = Null(())

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
            return {"error": f"Error writing property: {e}"}
        except TypeError as e:
            print(f"Type error while writing property: {e} - Value attempted: {value}")
            return {
                "error": f"Type error while writing property: {e} - Value attempted: {value}"
            }
        except Exception as e:
            print(
                f"Unexpected error while writing property: {e} - Value attempted: {value}"
            )
            return {
                "error": f"Unexpected error while writing property: {e} - Value attempted: {value}"
            }

    async def do_rpm(
        self,
        address: Address,
        *args: str,
    ):
        """
        Read Property Multiple (RPM) method to read multiple BACnet properties using vendor info.
        Returns a list of dictionaries with object identifiers, property identifiers,
        and either the value or a string describing an error.
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
                print(f"Unrecognized object type: {object_identifier}")
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
                print(f"Property reference: {property_reference}")

                # Check if the property is known
                if property_reference.propertyIdentifier not in (
                    PropertyIdentifier.all,
                    PropertyIdentifier.required,
                    PropertyIdentifier.optional,
                ):
                    property_type = object_class.get_property_type(
                        property_reference.propertyIdentifier
                    )
                    print(f"Property type: {property_type}")

                    if not property_type:
                        print(
                            f"Unrecognized property: {property_reference.propertyIdentifier}"
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
            print("Object identifier expected.")
            return [{"error": "Object identifier expected."}]

        try:
            # Perform the read property multiple operation
            response = await self.app.read_property_multiple(
                address_obj, parameter_list
            )
        except ErrorRejectAbortNack as err:
            print(f"Error during RPM: {err}")
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

        print("result_list ", result_list)

        return result_list
