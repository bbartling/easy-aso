import os
import asyncio
import re
from collections import OrderedDict
import yaml
from typing import Callable, List, Optional, Tuple

from bacpypes3.pdu import Address, IPv4Address
from bacpypes3.comm import bind

from bacpypes3.primitivedata import Integer
from bacpypes3.basetypes import PriorityValue
import bacpypes3

from bacpypes3.debugging import bacpypes_debugging, ModuleLogger
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.app import Application
from bacpypes3.console import Console
from bacpypes3.cmd import Cmd
from bacpypes3.primitivedata import Null, CharacterString, ObjectIdentifier
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
from bacpypes3.ipv4.bvll import Result as IPv4BVLLResult
from bacpypes3.ipv4.service import BVLLServiceAccessPoint, BVLLServiceElement

from enum import Enum

# some debugging
_debug = 0
_log = ModuleLogger(globals())

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
        For python bacnet-csv-logger
        Save the discovered points to a YAML file, named based on the instance ID,
        including the device name for the device identifier entry.
        If the device name is not found, default to the instance ID as a string.
        """
        config_dir = "configs"
        os.makedirs(config_dir, exist_ok=True)

        if filename is None:
            filename = f"{config_dir}/bacnet_config_{instance_id}.yaml"

        device_address, object_list, names_list = await self.do_point_discovery(
            instance_id
        )
        if not object_list:
            return

        if _debug:
            _log.debug(f" device_address {device_address}")
            _log.debug(f" len object_list {len(object_list)}")
            _log.debug(f" len names_list {len(names_list)}")

        # Combine object_list and names_list into a single structure
        points_data = []
        device_name = str(instance_id)  # Default to instance_id as string

        for index, (obj_type, obj_id) in enumerate(object_list):
            if _debug:
                _log.debug(f"index {index}")
                _log.debug(f"obj_type, obj_id {obj_type}, {obj_id}")

            name = names_list[index]
            point_data = {
                "object_identifier": f"{obj_type},{obj_id}",
                "object_name": name,
            }
            points_data.append(point_data)

            # Update the comparison to match the actual data types
            if isinstance(
                obj_type, Enum
            ):  # Replace 'Enum' with the actual type of obj_type, if necessary
                type_name = obj_type.name  # Or use the appropriate attribute/method
            else:
                type_name = str(obj_type)

            if type_name == "device" and obj_id == instance_id:
                device_name = name
                continue

        config_data = {
            "devices": [
                {
                    "device_identifier": str(instance_id),
                    "device_name": device_name,  # Add device name or instance_id here
                    "address": str(device_address),
                    "scrape_interval": 60,  # Default value
                    "read_multiple": True,  # Default value
                    "points": points_data,
                }
            ],
        }

        with open(filename, "w") as file:
            yaml.dump(config_data, file, default_flow_style=False)

        if _debug:
            _log.debug(f"Configuration for device {instance_id} saved to {filename}")

    async def do_point_discovery(
        self,
        instance_id: Optional[int] = None,
    ) -> List[ObjectIdentifier]:
        """
        Read the entire object list from a device at once, or if that fails, read
        the object identifiers one at a time.
        """
        # look for the device
        i_ams = await app.who_is(instance_id, instance_id)
        if not i_ams:
            return

        i_am = i_ams[0]
        if _debug:
            _log.debug("    - i_am: %r", i_am)

        device_address: Address = i_am.pduSource
        device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier
        vendor_info = get_vendor_info(i_am.vendorID)
        if _debug:
            _log.debug("    - device_address: %r", device_address)
            _log.debug("    - device_identifier: %r", device_identifier)
            _log.debug("    - vendor_info: %r", vendor_info)

        object_list = []
        names_list = []

        try:
            object_list = await app.read_property(
                device_address, device_identifier, "object-list"
            )

        except AbortPDU as err:
            if err.apduAbortRejectReason != AbortReason.segmentationNotSupported:
                _log.error(f"{device_identifier} object-list abort: {err}\n")
                return []
        except ErrorRejectAbortNack as err:
            _log.error(f"{device_identifier} object-list error/reject: {err}\n")
            return []

        if not object_list:

            if _debug:
                _log.debug(" Empty Object List Will Attempt Reading One By One")
                _log.debug(" This may take a minute....")
            else:
                print(" Empty Object List Will Attempt Reading One By One")
                print(" This may take a minute....")

            try:
                # read the length
                object_list_length = await app.read_property(
                    device_address,
                    device_identifier,
                    "object-list",
                    array_index=0,
                )

                # read each element individually
                for i in range(object_list_length):
                    object_identifier = await app.read_property(
                        device_address,
                        device_identifier,
                        "object-list",
                        array_index=i + 1,
                    )
                    object_list.append(object_identifier)

            except ErrorRejectAbortNack as err:
                _log.error(
                    f"{device_identifier} object-list length error/reject: {err}\n"
                )

        # loop thru each object and attempt to tease out the name
        for object_identifier in object_list:
            object_class = vendor_info.get_object_class(object_identifier[0])

            if _debug:
                _log.debug("    - object_class: %r", object_class)

            if object_class is None:
                _log.error(f"unknown object type: {object_identifier}\n")
                continue

            if _debug:
                _log.debug(f"    {object_identifier}:")

            try:

                property_value = await app.read_property(
                    device_address, object_identifier, "object-name"
                )
                if _debug:
                    _log.debug(f" {object_identifier}: {property_value}")
                else:
                    print(f" {object_identifier}: {property_value}")

                property_value_str = f"{property_value}"
                names_list.append(property_value_str)

            except bacpypes3.errors.InvalidTag as err:
                _log.error(f"Invalid Tag Error on point: {device_identifier}")
                names_list.append("ERROR - Delete this row")

            except ErrorRejectAbortNack as err:
                _log.error(f"{object_identifier} {object_identifier} error: {err}\n")

        if _debug:
            _log.debug("    - object_list: %r", object_list)
            _log.debug("    - names_list: %r", names_list)

        return device_address, object_list, names_list

    async def do_read_point_names(
        self,
        address: Address,
    ) -> None:
        """
        usage: read address objid prop[indx]
        """
        # read the property list
        property_list: Optional[List[PropertyIdentifier]] = None
        try:
            property_list = await app.read_property(
                address, object_identifier, "property-list"
            )
            if _debug:
                _log.debug("    - property_list: %r", property_list)
        except ErrorRejectAbortNack as err:

            _log.error(f"{object_identifier} property-list error: {err}\n")

        for object_identifier in property_list:

            if _debug:
                _log.debug(
                    "do_read_point_names %r %r %r",
                    address,
                    object_identifier,
                    "object-name",
                )

            try:
                response = await app.read_property(
                    address, object_identifier, "object-name"
                )
                if _debug:
                    _log.debug("    - len(response): %r", len(response))
                    _log.debug("    - response: %r", response)

                _log.debug(response)

            except ErrorRejectAbortNack as err:
                if _debug:
                    _log.debug("    - exception: %r", err)

            except Exception as e:
                _log.error(f"Other error while doing operation: {e}")


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

            # Discover points for the device
            try:
                device_address, object_list, names_list = await self.do_point_discovery(instance_id)
                if not object_list:
                    print(f"No points found for device {instance_id}")
                    continue

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

                    # Check if the object type supports priority arrays
                    if self.supports_priority_array(obj_type):
                        print(f"Reading priority array for point {object_identifier} ({point_name})")

                        try:
                            priority_array = await self.do_read_point_priority_arr(
                                device_address, object_identifier
                            )

                            # Add point data to the structure
                            point_data = {
                                "object_identifier": object_identifier,
                                "object_name": point_name,
                                "priority_array": priority_array,
                            }
                            device_data["points"].append(point_data)

                        except Exception as e:
                            print(f"Failed to read priority array for {object_identifier}: {e}")
                            continue
                    else:
                        print(f"Skipping read-only point {object_identifier} ({point_name})")

                # Save the device data to a file
                filename = f"device_{instance_id}_data.yaml"
                with open(filename, "w") as file:
                    yaml.dump(device_data, file, default_flow_style=False)

                print(f"Device {instance_id} data saved to {filename}")

            except Exception as e:
                print(f"Error discovering device {instance_id}: {e}")
                continue


    async def do_read_point_priority_arr(
        self,
        address: Address,
        object_identifier: ObjectIdentifier,
    ) -> None:
        """
        usage: read address objid prop[indx]
        """

        if _debug:
            _log.debug(
                "do_read_point_priority_arr %r %r %r",
                address,
                object_identifier,
                "priority-array",
            )

        try:
            response = await app.read_property(
                address, object_identifier, "priority-array"
            )
            if _debug:
                _log.debug("    - len(response): %r", len(response))
                _log.debug("    - response: %r", response)

            if response:
                _log.debug("Parsing response objects..")

                for index, priority_value in enumerate(response):
                    value_type = priority_value._choice
                    value = getattr(priority_value, value_type, None)

                    if value is not None:
                        if _debug:
                            _log.debug(
                                f"Priority level {index + 1}: {value_type} = {value}"
                            )
                        else:
                            print(f"Priority level {index + 1}: {value_type} = {value}")

        except ErrorRejectAbortNack as err:
            if _debug:
                _log.debug("    - exception: %r", err)

        except Exception as e:
            _log.error(f"Other error while doing operation: {e}")

    async def do_read(
        self,
        address: Address,
        object_identifier: ObjectIdentifier,
        property_identifier: str,
        property_array_index=None,  # Set the default value to None
    ) -> None:
        """
        usage: read address objid prop[indx]
        """

        if _debug:
            _log.debug(
                "do_read %r %r %r %r",
                address,
                object_identifier,
                property_identifier,
                property_array_index,
            )

        # split the property identifier and its index
        property_index_match = property_index_re.match(property_identifier)
        if not property_index_match:
            await self.response("property specification incorrect")
            return

        # split the property identifier and its index
        property_identifier, property_array_index = property_index_match.groups()
        if property_identifier.isdigit():
            property_identifier = int(property_identifier)
        if property_array_index is not None:
            property_array_index = int(property_array_index)

        try:
            property_value = await app.read_property(
                address, object_identifier, property_identifier, property_array_index
            )
            if _debug:
                _log.debug("    - property_value: %r", property_value)

        except ErrorRejectAbortNack as err:
            if _debug:
                _log.debug("    - exception: %r", err)
            property_value = err

        if isinstance(property_value, AnyAtomic):
            if _debug:
                _log.debug("    - schedule objects")
            property_value = property_value.get_value()

        await self.response(str(property_value))

    async def do_write(
        self,
        address: Address,
        object_identifier: ObjectIdentifier,
        property_identifier: str,
        value: str,
        priority: int = -1,
    ) -> None:
        """
        usage: write address objid prop[indx] value [ priority ]
        """
        if _debug:
            _log.debug(
                "do_write %r %r %r %r %r",
                address,
                object_identifier,
                property_identifier,
                value,
                priority,
            )

        # Manually add the command to the history list
        command = f"write {address} {object_identifier} {property_identifier} {value} {priority}"
        command_history.append(command)

        # split the property identifier and its index
        property_index_match = property_index_re.match(property_identifier)
        if not property_index_match:
            await self.response("property specification incorrect")
            return

        property_identifier, property_array_index = property_index_match.groups()
        if property_array_index is not None:
            property_array_index = int(property_array_index)

        if value == "null":
            if priority is None:
                raise ValueError("null only for overrides")
            value = Null(())

        try:
            response = await app.write_property(
                address,
                object_identifier,
                property_identifier,
                value,
                property_array_index,
                priority,
            )
            if _debug:
                _log.debug("    - response: %r", response)
            assert response is None

        except ErrorRejectAbortNack as err:
            if _debug:
                _log.debug("    - exception: %r", err)
            await self.response(str(err))

    async def do_iam(
        self,
        address: Optional[Address] = None,
    ) -> None:
        """
        Send an I-Am request, no response.

        usage: iam [ address ]
        """
        if _debug:
            _log.debug("do_iam %r", address)

        app.i_am(address)

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

    async def do_ihave(
        self,
        object_identifier: ObjectIdentifier,
        object_name: CharacterString,
        address: Optional[Address] = None,
    ) -> None:
        """
        Send an I-Have request.

        usage: ihave objid objname [ address ]
        """
        if _debug:
            _log.debug("do_ihave %r %r %r", object_identifier, object_name, address)

        app.i_have(object_identifier, object_name, address)

    async def do_rpm(
        self,
        address: Address,
        *args: str,
    ) -> None:
        """
        Read Property Multiple
        usage: rpm address ( objid ( prop[indx] )... )...
        """
        print(f" args {args}")
        args_list: List[str] = list(args)

        print(f" args_list {args_list}")

        # get information about the device from the cache
        device_info = await app.device_info_cache.get_device_info(address)

        # using the device info, look up the vendor information
        if device_info:
            vendor_info = get_vendor_info(device_info.vendor_identifier)
        else:
            vendor_info = get_vendor_info(0)

        parameter_list = []
        while args_list:
            # use the vendor information to translate the object identifier,
            # then use the object type portion to look up the object class
            object_identifier = vendor_info.object_identifier(args_list.pop(0))
            object_class = vendor_info.get_object_class(object_identifier[0])
            if not object_class:
                _log.debug(f" unrecognized object type: {object_identifier}")
                return

            # save this as a parameter
            parameter_list.append(object_identifier)

            property_reference_list = []
            while args_list:
                # use the vendor info to parse the property reference
                property_reference = PropertyReference(
                    args_list.pop(0),
                    vendor_info=vendor_info,
                )
                if _debug:
                    _log.debug("    - property_reference: %r", property_reference)

                if property_reference.propertyIdentifier not in (
                    PropertyIdentifier.all,
                    PropertyIdentifier.required,
                    PropertyIdentifier.optional,
                ):
                    property_type = object_class.get_property_type(
                        property_reference.propertyIdentifier
                    )
                    if _debug:
                        _log.debug("    - property_type: %r", property_type)
                        _log.debug(
                            "    - property_reference.propertyIdentifier: %r",
                            property_reference.propertyIdentifier,
                        )
                    if not property_type:
                        _log.debug(
                            f"unrecognized property: {property_reference.propertyIdentifier}"
                        )
                        return

                # save this as a parameter
                property_reference_list.append(property_reference)

                # crude check to see if the next thing is an object identifier
                if args_list and ((":" in args_list[0]) or ("," in args_list[0])):
                    break

            # save this as a parameter
            parameter_list.append(property_reference_list)

        if not parameter_list:
            await self.response("object identifier expected")
            return

        try:

            response = await app.read_property_multiple(address, parameter_list)

        except ErrorRejectAbortNack as err:
            if _debug:
                _log.debug("    - exception: %r", err)
            await self.response(str(err))
            return

        # dump out the results
        for (
            object_identifier,
            property_identifier,
            property_array_index,
            property_value,
        ) in response:
            if property_array_index is not None:
                await self.response(
                    f"{object_identifier} {property_identifier}[{property_array_index}] {property_value}"
                )
            else:
                await self.response(
                    f"{object_identifier} {property_identifier} {property_value}"
                )
            if isinstance(property_value, ErrorType):
                await self.response(
                    f"    {property_value.errorClass}, {property_value.errorCode}"
                )

    async def do_whois(
        self, low_limit: Optional[int] = None, high_limit: Optional[int] = None
    ) -> None:
        """
        Send a Who-Is request and wait for the response(s).

        usage: whois [ low_limit high_limit ]
        """
        if _debug:
            _log.debug("do_whois %r %r", low_limit, high_limit)

        i_ams = await app.who_is(low_limit, high_limit)
        if not i_ams:
            await self.response("No response(s)")
        else:
            for i_am in i_ams:
                if _debug:
                    _log.debug("    - i_am: %r", i_am)

                device_address: Address = i_am.pduSource
                device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier
                if _debug:
                    _log.debug(f"{device_identifier} @ {device_address}")
                else:
                    print(f"{device_identifier} @ {device_address}")

                try:
                    device_description: str = await app.read_property(
                        device_address, device_identifier, "description"
                    )
                    if _debug:
                        _log.debug(f"    description: {device_description}")
                    else:
                        print(f"description: {device_description}")

                except ErrorRejectAbortNack as err:
                    _log.error(f"{device_identifier} description error: {err}\n")

    async def do_who_is_router_to_network(
        self, address: Optional[Address] = None, network: Optional[int] = None
    ) -> None:
        """
        Who Is Router To Network
        usage: who_is_router_to_network [ address [ network ] ]
        """
        if _debug:
            _log.debug("do_wirtn %r %r", address, network)
        assert app.nse

        result_list: List[Tuple[NetworkAdapter, IAmRouterToNetwork]] = (
            await app.nse.who_is_router_to_network(destination=address, network=network)
        )
        if _debug:
            _log.debug("    - result_list: %r", result_list)
        if not result_list:
            raise RuntimeError("no response")

        report = []
        previous_source = None
        for adapter, i_am_router_to_network in result_list:
            if _debug:
                _log.debug("    - adapter: %r", adapter)
                _log.debug("    - i_am_router_to_network: %r", i_am_router_to_network)

            if i_am_router_to_network.npduSADR:
                npdu_source = i_am_router_to_network.npduSADR
                npdu_source.addrRoute = i_am_router_to_network.pduSource
            else:
                npdu_source = i_am_router_to_network.pduSource

            if (not previous_source) or (npdu_source != previous_source):
                report.append(str(npdu_source))
                previous_source = npdu_source

            report.append(
                "    "
                + ", ".join(
                    str(dnet) for dnet in i_am_router_to_network.iartnNetworkList
                )
            )

        await self.response("\n".join(report))


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
