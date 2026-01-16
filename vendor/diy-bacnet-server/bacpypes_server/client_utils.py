from typing import List, Union, Tuple, Optional
from bacpypes_server.errors import PointDiscoveryError

from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier, Null
from bacpypes3.apdu import (
    ErrorRejectAbortNack,
    PropertyReference,
    PropertyIdentifier,
    ErrorType,
    AbortPDU,
    AbortReason,
)
from bacpypes3.constructeddata import AnyAtomic, Sequence, Array, List
from bacpypes3.vendor import get_vendor_info
from bacpypes3.primitivedata import Atomic
from bacpypes3.json.util import (
    atomic_encode,
    sequence_to_json,
    extendedlist_to_json_list,
)
from bacpypes3.primitivedata import Null
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier
from bacpypes3.netservice import NetworkAdapter
from bacpypes3.npdu import IAmRouterToNetwork

from fastapi import HTTPException
import logging


logger = logging.getLogger("client_utils")


app = None  # will be set from main.py


def set_app(application):
    global app
    app = application


def _convert_to_address(address: str) -> Address:
    """
    Convert a string to a BACnet Address object.
    """
    return Address(address)


def _convert_to_object_identifier(obj_id: str) -> ObjectIdentifier:
    """
    Convert a string to a BACnet ObjectIdentifier.
    """
    object_type, instance_number = obj_id.split(",")
    return ObjectIdentifier((object_type.strip(), int(instance_number.strip())))


def parse_property_identifier(property_identifier):
    # Example parsing logic (modify as needed for your use case)
    if "," in property_identifier:
        prop_id, prop_index = property_identifier.split(",")
        return prop_id.strip(), int(prop_index.strip())
    return property_identifier, None


async def get_device_address(device_instance: int) -> Address:
    device_info = app.device_info_cache.instance_cache.get(device_instance, None)
    if device_info:
        return device_info.device_address

    i_ams = await app.who_is(device_instance, device_instance)
    if not i_ams:
        raise HTTPException(
            status_code=404, detail=f"Device {device_instance} not found"
        )
    if len(i_ams) > 1:
        raise HTTPException(
            status_code=400, detail=f"Multiple devices found: {device_instance}"
        )

    return i_ams[0].pduSource


async def bacnet_read(
    device_instance: int, object_identifier: str, property_identifier: str
):
    try:
        address = await get_device_address(device_instance)
        obj_id = ObjectIdentifier(object_identifier)

        value = await app.read_property(address, obj_id, property_identifier)

        if isinstance(value, AnyAtomic):
            value = value.get_value()

        if isinstance(value, Atomic):
            encoded = atomic_encode(value)
        elif isinstance(value, Sequence):
            encoded = sequence_to_json(value)
        elif isinstance(value, (Array, List)):
            encoded = extendedlist_to_json_list(value)
        else:
            raise HTTPException(
                status_code=400, detail=f"Unhandled type: {type(value)}"
            )

        return {property_identifier: encoded}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Read failed: {e}")


async def bacnet_write(
    device_instance: int,
    object_identifier: str,
    property_identifier: str,
    value: Union[float, int, str],
    priority: int = -1,
):
    try:
        address = await get_device_address(device_instance)
        obj_id = ObjectIdentifier(object_identifier)
        prop_id, prop_idx = parse_property_identifier(property_identifier)

        if value == "null":
            if priority is None:
                raise HTTPException(
                    status_code=400,
                    detail="Null requires a priority to release override",
                )
            value = Null(())

        result = await app.write_property(
            address, obj_id, prop_id, value, prop_idx, priority
        )
        return {"status": "success", "response": str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Write failed: {e}")


async def bacnet_rpm(
    address: Address,
    *args: str,
):

    logger.info(f"Received arguments for RPM: {args}")
    args_list: List[str] = list(args)

    # Convert address string to BACnet Address object
    address_obj = _convert_to_address(address)

    # Get device info from cache
    device_info = await app.device_info_cache.get_device_info(address_obj)

    # Look up vendor information
    vendor_info = get_vendor_info(device_info.vendor_identifier if device_info else 0)

    parameter_list = []
    while args_list:
        # Translate the object identifier using vendor information
        obj_id_str = args_list.pop(0)
        object_identifier = vendor_info.object_identifier(obj_id_str)
        object_class = vendor_info.get_object_class(object_identifier[0])

        if not object_class:
            logger.error(f"Unrecognized object type: {object_identifier}")
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
            logger.info(f"Property reference: {property_reference}")

            # Check if the property is known
            if property_reference.propertyIdentifier not in (
                PropertyIdentifier.all,
                PropertyIdentifier.required,
                PropertyIdentifier.optional,
            ):
                property_type = object_class.get_property_type(
                    property_reference.propertyIdentifier
                )
                logger.info(f"Property type: {property_type}")

                if not property_type:
                    logger.error(
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
        logger.error("Object identifier expected.")
        return [{"error": "Object identifier expected."}]

    try:
        # Perform the read property multiple operation
        response = await app.read_property_multiple(address_obj, parameter_list)
    except ErrorRejectAbortNack as err:
        logger.error(f"during RPM: {err}")
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

    logger.info(f"result_list: {result_list}")

    return result_list


async def perform_who_is(start_instance: int, end_instance: int):

    i_ams = await app.who_is(start_instance, end_instance)
    if not i_ams:
        no_response_str = f"No response(s) on WhoIs start_instance {start_instance} end_instance {end_instance}"
        logger.error(no_response_str)
        return no_response_str

    result = []
    for i_am in i_ams:
        logger.info("i_am: %r", i_am)

        device_address: Address = i_am.pduSource
        device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier

        logger.info(f"{device_identifier} @ {device_address}")

        try:
            device_description: str = await app.read_property(
                device_address, device_identifier, "description"
            )
            logger.info(f"description: {device_description}")
        except ErrorRejectAbortNack as err:
            # some devices don't support the "description" property
            device_description = f"Error: {err}"
            logger.info(f"ERROR - {device_identifier} description error: {err}")

        result.append(
            {
                "i-am-device-identifier": f"{device_identifier}",
                "device-address": f"{device_address}",
                "device-description": device_description,
                "max-apdu-length-accepted": i_am.maxAPDULengthAccepted,
                "segmentation-supported": str(i_am.segmentationSupported),
                "vendor-id": i_am.vendorID,
            }
        )

    return result


async def point_discovery(
    instance_id: Optional[int] = None,
) -> dict:
    try:
        i_ams = await app.who_is(instance_id, instance_id)
        if not i_ams:
            logger.warning(f"No response from device {instance_id}")
            raise PointDiscoveryError(
                data={
                    "instance": instance_id,
                    "detail": f"No response from device {instance_id} to Who-Is",
                }
            )

        i_am = i_ams[0]
        device_address: Address = i_am.pduSource
        device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier
        vendor_info = get_vendor_info(i_am.vendorID)

        object_list = []
        names_list = []

        try:
            object_list = await app.read_property(
                device_address, device_identifier, "object-list"
            )
            logger.info(f"Successfully read object list from {device_identifier}")
        except AbortPDU as err:
            if err.apduAbortRejectReason != AbortReason.segmentationNotSupported:
                logger.error(f"Abort reading object-list: {err}")
            return {
                "device_address": str(device_address),
                "objects": [],
            }
        except ErrorRejectAbortNack as err:
            logger.error(f"Error reading object-list: {err}")
            return {
                "device_address": str(device_address),
                "objects": [],
            }

        # fallback if object-list is empty
        if not object_list:
            try:
                length = await app.read_property(
                    device_address, device_identifier, "object-list", array_index=0
                )
                for i in range(length):
                    obj_id = await app.read_property(
                        device_address,
                        device_identifier,
                        "object-list",
                        array_index=i + 1,
                    )
                    object_list.append(obj_id)
            except ErrorRejectAbortNack as err:
                logger.error(f"Error reading object-list length: {err}")
                return {
                    "device_address": str(device_address),
                    "objects": [],
                }

        for obj_id in object_list:
            object_class = vendor_info.get_object_class(obj_id[0])
            if not object_class:
                logger.warning(f"Unknown object type: {obj_id}")
                continue
            try:
                name = await app.read_property(device_address, obj_id, "object-name")
                names_list.append(str(name))
            except Exception as err:
                logger.warning(f"Error reading name for {obj_id}: {err}")
                names_list.append("ERROR - Delete this row")

        return {
            "device_address": str(device_address),
            "objects": [
                {"object_identifier": str(oid), "name": name}
                for oid, name in zip(object_list, names_list)
            ],
        }

    except PointDiscoveryError:
        raise  # let it propagate cleanly
    except Exception as e:
        raise PointDiscoveryError(
            data={
                "instance": instance_id,
                "detail": f"Unexpected error during discovery: {e}",
            }
        )


async def read_point_priority_arr(
    address: Address, object_identifier: ObjectIdentifier
) -> Optional[List[dict]]:
    logger.info(f"Reading priority-array for {object_identifier} at {address}")
    try:
        response = await app.read_property(address, object_identifier, "priority-array")

        if not response:
            logger.info(f"No priority-array returned for {object_identifier}")
            return None

        parsed_priority_array = []
        for index, priority_value in enumerate(response):
            value_type = priority_value._choice
            value = getattr(priority_value, value_type, None)

            logger.debug(f"Priority {index+1}: type={value_type}, value={value}")

            # Always include every slot (even null)
            parsed_priority_array.append(
                {
                    "priority_level": index + 1,
                    "type": value_type,
                    "value": value if value is not None else None,
                }
            )

        return parsed_priority_array

    except ErrorRejectAbortNack as err:
        logger.error(f"BACnet error reading priority-array {object_identifier}: {err}")
    except Exception as e:
        logger.error(
            f"Unexpected error reading priority-array {object_identifier}: {e}"
        )
    return None


def normalize_object_type(bacnet_type: str) -> str:
    """
    Convert 'analog-value' or 'binary-output' → 'analogValue', 'binaryOutput', etc.
    """
    parts = bacnet_type.split("-")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def supports_priority_array(obj_type: str) -> bool:
    normalized = normalize_object_type(obj_type)
    return normalized in {
        "analogOutput",
        "binaryOutput",
        "analogValue",
        "binaryValue",
        "multiStateOutput",
        "multiStateValue",
    }


async def supervisory_logic_check(instance_id: int) -> dict:
    total_points = 0
    points_with_priority_array = 0
    points_without_priority_array = 0

    logger.info(f"🔍 Discovering device {instance_id}...")

    try:
        result = await point_discovery(instance_id)
        device_address = result["device_address"]
        objects = result["objects"]

        if device_address is None or not objects:
            logger.warning(f"No points found for device {instance_id}.")
            return {
                "device_id": instance_id,
                "address": None,
                "points": [],
                "summary": {
                    "total_points": 0,
                    "with_priority_array": 0,
                    "without_priority_array": 0,
                },
            }

        logger.info(f"Found {len(objects)} points for device {instance_id}")

        points = []

        for obj in objects:
            obj_type, obj_inst = obj["object_identifier"].split(",")
            object_id = ObjectIdentifier((obj_type, int(obj_inst)))
            point_name = obj["name"]
            total_points += 1

            if not supports_priority_array(obj_type):
                points_without_priority_array += 1
                logger.debug(f"⏩ {object_id} does not support priority array.")
                continue

            try:
                priority_array = await read_point_priority_arr(
                    Address(device_address), object_id
                )

                if not priority_array:
                    points_without_priority_array += 1
                    logger.info(f"No priority array for {object_id}")
                    continue

                points_with_priority_array += 1

                for idx, item in enumerate(priority_array):
                    if item.get("type") != "null":
                        value = item["value"]
                        value_str = {
                            "data_as_float": float(value),
                            "raw_data_type": value,
                        }
                        points.append(
                            {
                                "priority_level": idx + 1,
                                "object_identifier": str(object_id),
                                "object_name": point_name,
                                "type": item["type"],
                                "value": value_str,
                            }
                        )

            except Exception as e:
                msg = f"Error processing {object_id} ({point_name}): {e}"
                if "unknown-property" in str(e):
                    logger.debug(msg)
                    points_without_priority_array += 1
                else:
                    logger.warning(msg)
                continue

        logger.info("=" * 40)
        logger.info(f"Summary for device {instance_id}:")
        logger.info(f"Total Points: {total_points}")
        logger.info(f"With Priority Array: {points_with_priority_array}")
        logger.info(f"Without Priority Array: {points_without_priority_array}")
        logger.info("=" * 40)

        return {
            "device_id": instance_id,
            "address": device_address,
            "points": points,
            "summary": {
                "total_points": total_points,
                "with_priority_array": points_with_priority_array,
                "without_priority_array": points_without_priority_array,
            },
        }

    except TimeoutError as timeout_err:
        logger.error(f"Timeout for device {instance_id}: {timeout_err}")
    except Exception as e:
        logger.error(f"Discovery error for device {instance_id}: {e}")

    return {
        "device_id": instance_id,
        "address": None,
        "points": [],
        "summary": {
            "total_points": 0,
            "with_priority_array": 0,
            "without_priority_array": 0,
        },
    }


async def perform_who_is_router_to_network() -> List[dict]:
    logger.info(f"📡 Performing Who-Is-Router-To-Network broadcast")

    assert app.nse, "Network Service Element (NSE) not available."

    try:
        result_list: List[Tuple[NetworkAdapter, IAmRouterToNetwork]] = (
            await app.nse.who_is_router_to_network()
        )
    except Exception as e:
        logger.error(f"Error sending Who-Is-Router-To-Network: {e}")
        raise

    if not result_list:
        logger.info("No response received for Who-Is-Router-To-Network.")
        return []

    responses = []
    previous_source = None

    for adapter, i_am_router_to_network in result_list:
        npdu_source = (
            i_am_router_to_network.npduSADR or i_am_router_to_network.pduSource
        )
        if i_am_router_to_network.npduSADR:
            npdu_source.addrRoute = i_am_router_to_network.pduSource

        if not previous_source or npdu_source != previous_source:
            responses.append(
                {
                    "source": str(npdu_source),
                    "networks": i_am_router_to_network.iartnNetworkList,
                }
            )
            previous_source = npdu_source

    logger.info(f"Who-Is-Router-To-Network responses: {responses}")
    return responses
