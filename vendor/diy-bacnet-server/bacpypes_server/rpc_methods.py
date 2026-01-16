from bacpypes_server.models import (
    WritePropertyRequest,
    ReadMultiplePropertiesRequestWrapper,
    DeviceInstanceRange,
    SingleReadRequest,
    BaseResponse,
    PointUpdate,
    DeviceInstanceOnly,
    ReadPriorityArrayRequest,
    SupervisorySummary,
)
from bacpypes_server.client_utils import (
    bacnet_read,
    bacnet_write,
    bacnet_rpm,
    perform_who_is,
    get_device_address,
    point_discovery,
    supervisory_logic_check,
    read_point_priority_arr,
    perform_who_is_router_to_network,
)
from bacpypes_server.server_utils import (
    point_map,
    commandable_point_names,
    CommandableAnalogValueObject,
    CommandableBinaryValueObject,
)

from bacpypes_server.errors import (
    DeviceNotFoundError,
    WhoIsFailureError,
    PriorityArrayError,
    ReadPropertyError,
    WritePropertyError,
    RPMError,
    PointDiscoveryError,
    SupervisoryCheckError,
)

from bacpypes3.local.analog import AnalogValueObject
from bacpypes3.local.binary import BinaryValueObject
from bacpypes3.json.util import atomic_encode
from bacpypes3.primitivedata import ObjectIdentifier

import fastapi_jsonrpc as jsonrpc
import logging


logger = logging.getLogger("rpc_methods")

# This becomes the prefix path, like /bacnet
rpc = jsonrpc.Entrypoint("")


def parse_object_identifier(oid_str: str) -> ObjectIdentifier:
    try:
        obj_type, obj_inst = oid_str.split(",")
        return ObjectIdentifier((obj_type.strip(), int(obj_inst.strip())))
    except Exception as e:
        raise ValueError(f"Invalid object_identifier format: {oid_str}")


@rpc.method()
def server_hello() -> dict:
    return {"message": "BACnet RPC API ready. Use /docs to test."}


# ──────── BACNET SERVER UTILS METHODS ────────
@rpc.method()
def server_update_points(update: PointUpdate) -> dict:
    result = {}
    for name, value in update.root.items():

        if name in commandable_point_names:
            logger.warning(
                f"Skipping update to commandable point '{name}' to avoid conflict"
            )
            result[name] = (
                "skipped because point is configured as a writeable point in server object map"
            )
            continue

        obj = point_map.get(name)
        if obj is None:
            logger.warning(f"Point '{name}' not found in server object map")
            result[name] = "not found"
            continue
        try:
            if isinstance(obj, BinaryValueObject):
                desired_value = (
                    "active"
                    if value in [1, True, "true", "True", "active"]
                    else "inactive"
                )
                current_value = str(obj.presentValue).lower()
                if current_value != desired_value:
                    logger.info(
                        f"BV update: {name} changed from {current_value} → {desired_value}"
                    )
                    obj.presentValue = desired_value
                    result[name] = f"changed from {current_value} → {desired_value}"
                else:
                    logger.debug(f"BV unchanged: {name} = {current_value}")
            elif isinstance(obj, AnalogValueObject):
                new_value = float(value)
                current_value = float(obj.presentValue)
                if current_value != new_value:
                    logger.info(
                        f"AV update: {name} changed from {current_value} → {new_value}"
                    )
                    obj.presentValue = new_value
                    result[name] = f"changed from {current_value} → {new_value}"
                else:
                    logger.debug(f"AV unchanged: {name} = {current_value}")
        except Exception as e:
            logger.error(f"Error updating {name}: {e}")
            result[name] = f"error: {e}"
    return {"updated_bacnet_points": result}


@rpc.method()
def server_read_commandable() -> dict:
    result = {}
    for name, obj in point_map.items():
        if isinstance(
            obj, (CommandableAnalogValueObject, CommandableBinaryValueObject)
        ):
            try:
                value = obj.presentValue
                result[name] = (
                    float(value)
                    if isinstance(obj, CommandableAnalogValueObject)
                    else str(value)
                )
            except Exception as e:
                logger.error(f"Error reading {name}: {e}")
                result[name] = f"error: {e}"
    return result


@rpc.method()
def server_read_all_values() -> dict:
    result = {}
    for name, obj in point_map.items():
        try:
            val = obj.presentValue
            result[name] = atomic_encode(val) if hasattr(val, "encode") else str(val)
        except Exception as e:
            logger.error(f"Error reading {name}: {e}")
            result[name] = f"error: {e}"
    return result


# ──────── BACNET CLIENT UTILS METHODS ────────


@rpc.method()
async def client_read_property(request: SingleReadRequest) -> dict:
    try:
        return await bacnet_read(
            request.device_instance,
            request.object_identifier,
            request.property_identifier,
        )
    except Exception as e:
        logger.error(f"Read property failed: {e}")
        raise ReadPropertyError(
            data={"object_identifier": request.object_identifier, "detail": str(e)}
        )


@rpc.method()
async def client_write_property(request: WritePropertyRequest) -> dict:
    try:
        return await bacnet_write(
            device_instance=request.device_instance,
            object_identifier=request.object_identifier,
            property_identifier=request.property_identifier,
            value=request.value,
            priority=request.priority or -1,
        )
    except Exception as e:
        logger.error(f"Write property failed: {e}")
        raise WritePropertyError(
            data={"object_identifier": request.object_identifier, "detail": str(e)}
        )


@rpc.method()
async def client_read_multiple(
    request: ReadMultiplePropertiesRequestWrapper,
) -> BaseResponse:
    try:
        address = await get_device_address(request.device_instance)
    except Exception as e:
        logger.error(f"Could not resolve device address: {e}")
        raise DeviceNotFoundError(
            data={"instance": request.device_instance, "detail": str(e)}
        )

    args = []
    for r in request.requests:
        args.append(r.object_identifier)
        args.append(r.property_identifier)

    try:
        result = await bacnet_rpm(address, *args)
        return BaseResponse(
            success=True,
            message="Read Multiple complete",
            data={"results": result},
        )
    except Exception as e:
        logger.error(f"RPM failed: {e}")
        # Still a generic error here — can define RPMError later if needed
        raise RPMError(data={"instance": request.device_instance, "detail": str(e)})


@rpc.method()
async def client_whois_range(request: DeviceInstanceRange) -> BaseResponse:
    try:
        data = await perform_who_is(
            start_instance=request.start_instance,
            end_instance=request.end_instance,
        )
        return BaseResponse(
            success=True, message="Who-Is scan complete", data={"devices": data}
        )
    except Exception as e:
        logger.error(f"Who-Is scan failed: {e}")
        raise WhoIsFailureError(
            data={
                "detail": str(e),
                "start_instance": request.start_instance,
                "end_instance": request.end_instance,
            }
        )


@rpc.method()
async def client_point_discovery(instance: DeviceInstanceOnly) -> BaseResponse:
    try:
        data = await point_discovery(instance.device_instance)
        return BaseResponse(
            success=True,
            message="Point discovery successful",
            data=data,
        )
    except PointDiscoveryError:
        raise  # Re-raise it cleanly without nesting
    except Exception as e:
        raise PointDiscoveryError(
            data={
                "instance": instance.device_instance,
                "detail": f"Unexpected error during point discovery: {e}",
            }
        )


@rpc.method()
async def client_supervisory_logic_checks(
    instance: DeviceInstanceOnly,
) -> SupervisorySummary:
    try:
        return await supervisory_logic_check(instance.device_instance)
    except Exception as e:
        raise SupervisoryCheckError(
            data={"instance": instance.device_instance, "detail": str(e)}
        )


@rpc.method()
async def client_read_point_priority_array(request: ReadPriorityArrayRequest) -> list:
    logger.info(
        f"Reading priority array for device_instance={request.device_instance}, object_identifier={request.object_identifier}"
    )
    try:
        address = await get_device_address(request.device_instance)
        object_id = parse_object_identifier(request.object_identifier)
        priority_array = await read_point_priority_arr(address, object_id)

        if priority_array is None:
            raise PriorityArrayError(
                data={"detail": "No priority array found or empty response"}
            )

        return priority_array

    except PriorityArrayError:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error reading priority-array {request.object_identifier}: {e}"
        )
        raise PriorityArrayError(data={"detail": str(e)})


@rpc.method()
async def client_whois_router_to_network() -> BaseResponse:
    try:
        results = await perform_who_is_router_to_network()
        return BaseResponse(
            success=True,
            message="Who-Is-Router-To-Network scan complete",
            data={"routers": results},
        )
    except Exception as e:
        logger.error(f"Who-Is-Router-To-Network failed: {e}")
        raise WhoIsFailureError(data={"detail": str(e)})
