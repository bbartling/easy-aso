import os
import asyncio
import re
import yaml
from typing import Callable, List, Any, Optional, Tuple


from bacpypes3.pdu import Address
from bacpypes3.comm import bind
import bacpypes3

from bacpypes3.debugging import bacpypes_debugging, ModuleLogger
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.app import Application
from bacpypes3.console import Console
from bacpypes3.cmd import Cmd
from bacpypes3.primitivedata import Null, ObjectIdentifier
from bacpypes3.npdu import IAmRouterToNetwork
from bacpypes3.comm import bind
from typing import Callable, Optional, List
from bacpypes3.constructeddata import AnyAtomic
from bacpypes3.apdu import (
    ErrorRejectAbortNack,
    PropertyReference,
    PropertyIdentifier,
    ErrorType,
)
from bacpypes3.vendor import get_vendor_info
from bacpypes3.basetypes import PropertyIdentifier
from bacpypes3.apdu import AbortReason, AbortPDU, ErrorRejectAbortNack
from bacpypes3.netservice import NetworkAdapter

# for BVLL services
from bacpypes3.ipv4.service import BVLLServiceElement

from enum import Enum

# some debugging
_debug = 0

# 'property[index]' matching
property_index_re = re.compile(r"^([A-Za-z-]+)(?:\[([0-9]+)\])?$")

# globals
app: Application

# globals
show_warnings: bool = False
app: Optional[Application] = None
bvll_ase: Optional[BVLLServiceElement] = None

# Define a list to store command history
command_history = []

DEFAULT_SCRAPE_INTERVAL = 300  # seconds


@bacpypes_debugging
class SampleCmd(Cmd):
    """
    Sample Cmd
    """

    _debug: Callable[..., None]


    async def do_save_device_yaml_config(self, instance_id: int, filename=None):
        """
        Save the discovered points to a YAML file, named based on the instance ID,
        including the device name for the device identifier entry.
        If the device name is not found, default to the instance ID as a string.
        """
        # Create the configs directory if it doesn't exist
        config_dir = "configs"
        os.makedirs(config_dir, exist_ok=True)

        # If no filename is provided, create a default one
        if filename is None:
            filename = f"{config_dir}/bacnet_config_{instance_id}.yaml"

        # Discover points for the device
        device_address, object_list, names_list = await self.do_point_discovery(instance_id)
        if not object_list:
            print(f"No points discovered for device {instance_id}, skipping file save.")
            return

        print(f"Device address: {device_address}")
        print(f"Number of objects discovered: {len(object_list)}")
        print(f"Number of names discovered: {len(names_list)}")

        # Combine object_list and names_list into a single structure
        points_data = []
        device_name = str(instance_id)  # Default to instance_id as the device name

        # Loop through the object list and associate with names
        for index, (obj_type, obj_id) in enumerate(object_list):
            name = names_list[index]
            print(f"Processing object {index + 1}: {obj_type}, {obj_id} - Name: {name}")

            # Create point data dictionary
            point_data = {
                "object_identifier": f"{obj_type},{obj_id}",
                "object_name": name,
            }
            points_data.append(point_data)

            # Update the device_name if it's a device object
            if isinstance(obj_type, Enum):  # Ensure obj_type is an Enum, if applicable
                type_name = obj_type.name  # Retrieve the name of the Enum member
            else:
                type_name = str(obj_type)

            if type_name == "device" and obj_id == instance_id:
                device_name = name  # Update the device name

        # Prepare the configuration data for the device
        config_data = {
            "devices": [
                {
                    "device_identifier": str(instance_id),
                    "device_name": device_name,  # Use the found device name or instance_id
                    "address": str(device_address),
                    "scrape_interval": 60,  # Default value
                    "read_multiple": True,  # Default value
                    "points": points_data,
                }
            ],
        }

        # Save the configuration to a YAML file
        with open(filename, "w") as file:
            yaml.dump(config_data, file, default_flow_style=False)

        print(f"Configuration for device {instance_id} saved to {filename}")


    async def do_point_discovery(
        self,
        instance_id: Optional[int] = None,
    ) -> Tuple[Optional[Address], List[ObjectIdentifier], List[str]]:
        """
        Read the entire object list from a device at once, or if that fails, read
        the object identifiers one at a time.
        """
        # Perform the who-is operation and get the response
        i_ams = await app.who_is(instance_id, instance_id)
        if not i_ams:
            print(f"No response from device {instance_id}.")
            return None, [], []  # Return empty values if no response is found

        i_am = i_ams[0]
        device_address: Address = i_am.pduSource
        device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier
        vendor_info = get_vendor_info(i_am.vendorID)

        object_list = []
        names_list = []

        print(f"Device address: {device_address}")

        # Try reading the object-list property
        try:
            object_list = await app.read_property(
                device_address, device_identifier, "object-list"
            )
            print(f"Successfully read object list from {device_identifier}")
        except AbortPDU as err:
            if err.apduAbortRejectReason != AbortReason.segmentationNotSupported:
                print(f"Error reading object-list for {device_identifier}: {err}")
            return device_address, [], []  # Return empty if object-list read fails
        except ErrorRejectAbortNack as err:
            print(f"Error/reject reading object-list for {device_identifier}: {err}")
            return device_address, [], []

        # If the object list is empty, attempt to read it one by one
        if not object_list:
            try:
                object_list_length = await app.read_property(
                    device_address, device_identifier, "object-list", array_index=0
                )
                print(f"Object list length: {object_list_length}")

                for i in range(object_list_length):
                    object_identifier = await app.read_property(
                        device_address,
                        device_identifier,
                        "object-list",
                        array_index=i + 1,
                    )
                    print(f"Object identifier {i+1}: {object_identifier}")
                    object_list.append(object_identifier)

            except ErrorRejectAbortNack as err:
                print(f"Error/reject reading object-list length for {device_identifier}: {err}")
                return device_address, [], []

        # Try reading the object names
        for object_identifier in object_list:
            object_class = vendor_info.get_object_class(object_identifier[0])
            if object_class is None:
                print(f"Unknown object type for {object_identifier}, skipping...")
                continue

            try:
                property_value = await app.read_property(
                    device_address, object_identifier, "object-name"
                )
                print(f"Object: {object_identifier} - Name: {property_value}")
                names_list.append(str(property_value))
            except bacpypes3.errors.InvalidTag as err:
                print(f"Invalid tag error on point {device_identifier}. Adding placeholder.")
                names_list.append("ERROR - Delete this row")
            except ErrorRejectAbortNack as err:
                print(f"Error/reject reading object-name for {object_identifier}: {err}")
                names_list.append("ERROR - Delete this row")

        return device_address, object_list, names_list



    def supports_priority_array(self, obj_type: str) -> bool:
        """
        Check if the given object type supports the priority array.
        Only certain object types, such as AO, BO, AV, BV, and multi-state output, support priority arrays.
        """
        return obj_type in {
            "analogOutput",
            "binaryOutput",
            "analogValue",
            "binaryValue",
            "multiStateOutput",
            "multiStateValue",
        }



    async def do_supervisory_logic_checks(self, start_id: int, end_id: int):
        """
        Discover devices in a range of BACnet instance IDs, retrieve points,
        check priority arrays (if supported), and save the data to files.
        """
        for instance_id in range(start_id, end_id + 1):
            print(f"Discovering device {instance_id}...")

            try:
                device_address, object_list, names_list = await self.do_point_discovery(instance_id)

                if device_address is None or not object_list:
                    print(f"No points found for device {instance_id}, skipping...")
                    continue  # Skip to the next device if no points are found

                print(f"Discovered {len(object_list)} points for device {instance_id}")

                # Prepare data structure for storing information
                device_data = {
                    "device_id": instance_id,
                    "address": str(device_address),
                    "points": [],
                }

                # Loop through each point and read priority array (if supported)
                for index, (obj_type, obj_id) in enumerate(object_list):
                    object_identifier = f"{obj_type},{obj_id}"
                    point_name = names_list[index]
                    print(f"Checking if {object_identifier} ({point_name}) supports priority array")

                    try:
                        priority_array = await self.do_read_point_priority_arr(device_address, (obj_type, obj_id))

                        prior_array_index = 0

                        # Simplify the priority array to only include priority, type, and value
                        for item in priority_array:
                            value = item.get('value')
                            type_ = item.get('type')

                            # Only keep the entries with non-null values
                            if type_ != 'null':
                                value_str = str(value)
                                point_data = {
                                    "priority_level": prior_array_index + 1,
                                    "object_identifier": object_identifier,
                                    "object_name": point_name,
                                    "type": type_,
                                    "value": value_str
                                }
                                device_data["points"].append(point_data)

                    except KeyError as key_err:
                        print(f"KeyError while processing {object_identifier}: {key_err}")
                    except TypeError as type_err:
                        print(f"TypeError while processing {object_identifier}: {type_err}")
                    except TimeoutError as timeout_err:
                        print(f"Timeout while reading priority array for {object_identifier}: {timeout_err}")
                    except Exception as e:
                        print(f"Unexpected error for {object_identifier}: {e}")
                        continue  # Skip to the next point if there's an error

                # Only save the device data to a file if there are points with valid priority arrays
                if device_data["points"]:
                    filename = f"device_{instance_id}_data.yaml"
                    with open(filename, "w") as file:
                        yaml.dump(device_data, file, default_flow_style=False)
                    print(f"Device {instance_id} data saved to {filename}")
                else:
                    print(f"No points with non-null values for device {instance_id}, skipping file save.")

            except TimeoutError as timeout_err:
                print(f"Timeout occurred for device {instance_id}: {timeout_err}")
            except Exception as e:
                print(f"Error discovering device {instance_id}: {e}")



    async def do_read_point_priority_arr(
        self,
        address: Address,
        object_identifier: ObjectIdentifier,
    ) -> None:
        """
        Read the priority array property of a BACnet object and return its values.

        Returns a list of priority values, where each entry is a dictionary with the level and value.
        """
        try:
            # Read the priority array property
            response = await app.read_property(
                address, object_identifier, "priority-array"
            )
            
            if response:
                parsed_priority_array = []

                # Parse each entry in the priority array
                for index, priority_value in enumerate(response):
                    value_type = priority_value._choice
                    value = getattr(priority_value, value_type, None)

                    if value is not None:
                        priority_level_data = {
                            "level": index + 1,  # Priority levels start from 1
                            "type": value_type,
                            "value": value
                        }
                        parsed_priority_array.append(priority_level_data)

                        # Print the parsed priority level and value
                        print(f"Priority level {index + 1}: {value_type} = {value}")

                return parsed_priority_array

        except ErrorRejectAbortNack as err:
            print(f"Error reading priority array for {object_identifier}: {err}")
            return None

        except Exception as e:
            print(f"An unexpected error occurred while reading priority array for {object_identifier}: {e}")
            return None


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

        print(f"Reading {property_identifier} from {object_identifier} at {address}...")

        # Split the property identifier and its index
        property_index_match = property_index_re.match(property_identifier)
        if not property_index_match:
            print("Property specification incorrect")
            return None

        property_identifier, property_array_index = property_index_match.groups()
        
        # Convert to integer if the property identifier is numeric
        if property_identifier.isdigit():
            property_identifier = int(property_identifier)
        
        # Convert array index to integer if it exists
        if property_array_index is not None:
            property_array_index = int(property_array_index)

        try:
            # Read the property value
            property_value = await app.read_property(
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
        """
        Write a property value to a BACnet object.
        """
        print(f"Writing {value} to {property_identifier} at {object_identifier} on {address} with priority {priority}...")

        # Manually add the command to the history list
        command = f"write {address} {object_identifier} {property_identifier} {value} {priority}"
        command_history.append(command)

        # Split the property identifier and its index
        property_index_match = property_index_re.match(property_identifier)
        if not property_index_match:
            print("Property specification incorrect")
            return

        property_identifier, property_array_index = property_index_match.groups()
        
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
            response = await app.write_property(
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


    async def do_whohas(
        self,
        *args: str,
    ) -> None:
        """
        Send a Who-Has request, an objid or objname (or both) is required.

        usage: whohas [ low_limit high_limit ] [ objid ] [ objname ] [ address ]
        """
        if _debug:
            _log.debug("do_whohas %r", args)

        if not args:
            raise RuntimeError("object-identifier or object-name expected")
        args_list: List[str] = list(args)

        if args_list[0].isdigit():
            low_limit = int(args_list.pop(0))
        else:
            low_limit = None
        if args_list[0].isdigit():
            high_limit = int(args_list.pop(0))
        else:
            high_limit = None
        if _debug:
            _log.debug("    - low_limit, high_limit: %r, %r", low_limit, high_limit)

        if not args_list:
            raise RuntimeError("object-identifier expected")
        try:
            object_identifier = ObjectIdentifier(args_list[0])
            del args_list[0]
        except ValueError:
            object_identifier = None
        if _debug:
            _log.debug("    - object_identifier: %r", object_identifier)

        if len(args_list) == 0:
            object_name = address = None
        elif len(args_list) == 2:
            object_name = args_list[0]
            address = Address(args_list[1])
        elif len(args_list) == 1:
            try:
                address = Address(args_list[0])
                object_name = None
            except ValueError:
                object_name = args_list[0]
                address = None
        else:
            raise RuntimeError("unrecognized arguments")
        if _debug:
            _log.debug("    - object_name: %r", object_name)
            _log.debug("    - address: %r", address)

        i_haves = await app.who_has(
            low_limit, high_limit, object_identifier, object_name, address
        )
        if not i_haves:
            await self.response("No response(s)")
        else:
            for i_have in i_haves:
                if _debug:
                    _log.debug("    - i_have: %r", i_have)
                await self.response(
                    f"{i_have.deviceIdentifier[1]} {i_have.objectIdentifier} {i_have.objectName!r}"
                )

    async def do_whohas(self, *args: str) -> None:
        """
        Send a Who-Has request, an objid or objname (or both) is required.

        usage: whohas [ low_limit high_limit ] [ objid ] [ objname ] [ address ]
        """
        if not args:
            raise RuntimeError("object-identifier or object-name expected")
        
        args_list: List[str] = list(args)

        # Handle low and high limits if present
        low_limit = int(args_list.pop(0)) if args_list and args_list[0].isdigit() else None
        high_limit = int(args_list.pop(0)) if args_list and args_list[0].isdigit() else None

        print(f"Low limit: {low_limit}, High limit: {high_limit}")

        if not args_list:
            raise RuntimeError("object-identifier expected")

        # Parse object_identifier or object_name
        try:
            object_identifier = ObjectIdentifier(args_list[0])
            del args_list[0]
        except ValueError:
            object_identifier = None

        print(f"Object Identifier: {object_identifier}")

        # Determine object name and address based on remaining arguments
        if len(args_list) == 2:
            object_name = args_list[0]
            address = Address(args_list[1])
        elif len(args_list) == 1:
            try:
                address = Address(args_list[0])
                object_name = None
            except ValueError:
                object_name = args_list[0]
                address = None
        else:
            object_name = address = None

        print(f"Object Name: {object_name}, Address: {address}")

        # Send the Who-Has request
        i_haves = await app.who_has(low_limit, high_limit, object_identifier, object_name, address)

        # Handle responses
        if not i_haves:
            print("No response(s)")
        else:
            for i_have in i_haves:
                print(f"Device {i_have.deviceIdentifier[1]} has {i_have.objectIdentifier} named {i_have.objectName!r}")


    async def do_rpm(
        self,
        address: Address,
        *args: str,
    ) -> None:
        """
        Read Property Multiple
        usage: rpm address ( objid ( prop[indx] )... )...
        """
        print(f"Received arguments: {args}")
        args_list: List[str] = list(args)

        print(f"Args list: {args_list}")

        # Get device info from cache
        device_info = await app.device_info_cache.get_device_info(address)

        # Look up vendor information
        vendor_info = get_vendor_info(device_info.vendor_identifier if device_info else 0)

        parameter_list = []
        while args_list:
            # Translate the object identifier using vendor information
            object_identifier = vendor_info.object_identifier(args_list.pop(0))
            object_class = vendor_info.get_object_class(object_identifier[0])

            if not object_class:
                print(f"Unrecognized object type: {object_identifier}")
                return

            # Save this object identifier as a parameter
            parameter_list.append(object_identifier)

            property_reference_list = []
            while args_list:
                # Parse the property reference using vendor info
                property_reference = PropertyReference(
                    args_list.pop(0),
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
                        print(f"Unrecognized property: {property_reference.propertyIdentifier}")
                        return

                # Save this property reference as a parameter
                property_reference_list.append(property_reference)

                # Break if the next thing is an object identifier
                if args_list and ((":" in args_list[0]) or ("," in args_list[0])):
                    break

            # Save the property reference list as a parameter
            parameter_list.append(property_reference_list)

        if not parameter_list:
            print("Object identifier expected")
            return

        try:
            # Perform the read property multiple operation
            response = await app.read_property_multiple(address, parameter_list)
        except ErrorRejectAbortNack as err:
            print(f"Error during RPM: {err}")
            return

        # Print out the results
        for object_identifier, property_identifier, property_array_index, property_value in response:
            if property_array_index is not None:
                print(f"{object_identifier} {property_identifier}[{property_array_index}] = {property_value}")
            else:
                print(f"{object_identifier} {property_identifier} = {property_value}")

            if isinstance(property_value, ErrorType):
                print(f"    Error: {property_value.errorClass}, {property_value.errorCode}")


    async def do_whois(
        self, low_limit: Optional[int] = None, high_limit: Optional[int] = None
    ) -> None:
        """
        Send a Who-Is request and wait for the response(s).

        usage: whois [ low_limit high_limit ]
        """
        print(f"Sending Who-Is request with low limit: {low_limit}, high limit: {high_limit}")

        # Send the Who-Is request
        i_ams = await app.who_is(low_limit, high_limit)
        
        if not i_ams:
            print("No response(s) received")
        else:
            # Loop through responses
            for i_am in i_ams:
                device_address: Address = i_am.pduSource
                device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier

                print(f"Device {device_identifier} found at {device_address}")

                # Try reading the device description
                try:
                    device_description: str = await app.read_property(
                        device_address, device_identifier, "description"
                    )
                    print(f"Description: {device_description}")

                except ErrorRejectAbortNack as err:
                    print(f"Error reading description for {device_identifier}: {err}")


    async def do_who_is_router_to_network(
        self, address: Optional[Address] = None, network: Optional[int] = None
    ) -> None:
        """
        Who Is Router To Network
        usage: who_is_router_to_network [ address [ network ] ]
        """
        print(f"Sending Who-Is-Router-To-Network request to address: {address}, network: {network}")
        assert app.nse  # Ensure the network service element is available

        # Send the request and await the response
        result_list: List[Tuple[NetworkAdapter, IAmRouterToNetwork]] = (
            await app.nse.who_is_router_to_network(destination=address, network=network)
        )

        # Check if we received any responses
        if not result_list:
            print("No response received")
            return

        report = []
        previous_source = None

        # Process the results
        for adapter, i_am_router_to_network in result_list:
            print(f"Adapter: {adapter}")
            print(f"Router to Network response: {i_am_router_to_network}")

            if i_am_router_to_network.npduSADR:
                npdu_source = i_am_router_to_network.npduSADR
                npdu_source.addrRoute = i_am_router_to_network.pduSource
            else:
                npdu_source = i_am_router_to_network.pduSource

            # Add the source to the report if it's different from the previous one
            if not previous_source or npdu_source != previous_source:
                report.append(str(npdu_source))
                previous_source = npdu_source

            # Append the network list to the report
            report.append(
                "    " + ", ".join(str(dnet) for dnet in i_am_router_to_network.iartnNetworkList)
            )

        # Print the report
        print("\n".join(report))


async def main() -> None:
    global app

    app = None
    try:
        parser = SimpleArgumentParser()
        args = parser.parse_args()
        if _debug:
            _log.debug("args: %r", args)

        # build a very small stack
        console = Console()
        cmd = SampleCmd()
        bind(console, cmd)

        # build an application
        app = Application.from_args(args)
        if _debug:
            _log.debug("app: %r", app)

        # wait until the user is done
        await console.fini.wait()

    except KeyboardInterrupt:
        if _debug:
            _log.debug("keyboard interrupt")
    finally:
        if app:
            app.close()


if __name__ == "__main__":
    asyncio.run(main())
