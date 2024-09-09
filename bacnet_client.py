from contextlib import asynccontextmanager
from bacpypes3.debugging import ModuleLogger
from bacpypes3.app import Application
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier, Null
from bacpypes3.constructeddata import Sequence, Array, List as BacpypesList
from bacpypes3.apdu import ErrorRejectAbortNack
from bacpypes3.json.util import sequence_to_json, extendedlist_to_json_list  # Importing from BACpypes3

from models import (
    WritePropertyRequest,
    ReadMultiplePropertiesRequest,
    DeviceInstanceValidator,
    nan_or_inf_check,
    ReadMultiplePropertiesRequestWrapper,
    DeviceInstanceRange
)
from pydantic import ValidationError

_log = ModuleLogger(globals())


class BACnetClient:
    def __init__(self):
        self.service = None
    
    @asynccontextmanager
    async def manage_bacnet_service(self):
        self.service = Application()
        yield
    
    async def get_device_address(self, device_instance: int) -> Address:
        # Validate device instance using Pydantic model
        try:
            DeviceInstanceValidator(device_instance=device_instance)
        except ValidationError as e:
            raise ValueError(f"Invalid device instance: {e}")
        
        device_info = self.service.device_info_cache.instance_cache.get(device_instance, None)
        if device_info:
            device_address = device_info.device_address
            _log.debug(f" gda - Cached address: {device_address}")
        else:
            i_ams = await self.service.who_is(device_instance, device_instance)
            if not i_ams:
                raise ValueError(f" gda - Device not found: {device_instance}")
            if len(i_ams) > 1:
                raise ValueError(f" gda - Multiple devices found: {device_instance}")
            device_address = i_ams[0].pduSource
            _log.debug(f" gda - Resolved address: {device_address}")
        return device_address

    async def read_property(self, device_instance: int, object_identifier: str, property_identifier: str):
        # Validate using Pydantic model before proceeding
        try:
            WritePropertyRequest(
                device_instance=device_instance,
                object_identifier=object_identifier,
                property_identifier=property_identifier,
                value=None  # value is not needed for read
            )
        except ValidationError as e:
            raise ValueError(f"Invalid read request: {e}")
        
        device_address = await self.get_device_address(device_instance)

        try:
            property_value = await self.service.read_property(
                device_address, ObjectIdentifier(object_identifier), property_identifier
            )
        except ErrorRejectAbortNack as err:
            return f"BACnet error/reject/abort: {err}"

        if isinstance(property_value, Sequence):
            encoded_value = sequence_to_json(property_value)
        elif isinstance(property_value, (Array, BacpypesList)):
            encoded_value = extendedlist_to_json_list(property_value)
        else:
            return f"JSON encoding: {property_value}"

        encoded_value = nan_or_inf_check(encoded_value)
        return encoded_value

    async def write_property(self, device_instance: int, object_identifier: str, property_identifier: str, value: str, priority: int = -1):
        # Validate using Pydantic model before proceeding
        try:
            WritePropertyRequest(
                device_instance=device_instance,
                object_identifier=object_identifier,
                property_identifier=property_identifier,
                value=value,
                priority=priority
            )
        except ValidationError as e:
            raise ValueError(f"Invalid write request: {e}")
        
        device_address = await self.get_device_address(device_instance)

        if value == "null":
            if priority is None:
                return "BACnet Error: null is only for releasing overrides and requires a priority"
            value = Null(())

        try:
            object_identifier = ObjectIdentifier(object_identifier)
        except ErrorRejectAbortNack as err:
            return str(err)

        try:
            response = await self.service.write_property(
                device_address,
                object_identifier,
                property_identifier,
                value,
                None,
                priority,
            )
            return response
        except ErrorRejectAbortNack as err:
            return str(err)

    async def perform_who_is(self, start_instance: int, end_instance: int):
        # Validate device instance range using Pydantic
        try:
            DeviceInstanceRange(start_instance=start_instance, end_instance=end_instance)
        except ValidationError as e:
            raise ValueError(f"Invalid device instance range: {e}")

        try:
            i_ams = await self.service.who_is(start_instance, end_instance)
            if not i_ams:
                return f"No response for WhoIs from {start_instance} to {end_instance}"
            
            result = []
            for i_am in i_ams:
                device_address: Address = i_am.pduSource
                device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier

                try:
                    device_description = await self.service.read_property(
                        device_address, device_identifier, "description"
                    )
                except ErrorRejectAbortNack as err:
                    device_description = f"Error: {err}"

                result.append({
                    "device_identifier": f"{device_identifier}",
                    "device_address": f"{device_address}",
                    "device_description": device_description,
                    "vendor_id": i_am.vendorID,
                })
            return result
        except Exception as e:
            _log.error(f"Exception in perform_who_is: {e}")
            return str(e)

    async def point_discovery(self, device_instance: int):
        # Validate device instance
        try:
            DeviceInstanceValidator(device_instance=device_instance)
        except ValidationError as e:
            raise ValueError(f"Invalid device instance: {e}")

        try:
            i_ams = await self.service.who_is(device_instance, device_instance)
            if not i_ams:
                return

            i_am = i_ams[0]
            device_address: Address = i_am.pduSource
            device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier

            object_list = await self.service.read_property(device_address, device_identifier, "object-list")
            if isinstance(object_list, str) and "no object class" in object_list:
                object_list_length = await self.service.read_property(
                    device_address,
                    device_identifier,
                    "object-list",
                    array_index=0,
                )
                object_list_length = int(object_list_length)
                for i in range(object_list_length):
                    object_identifier = await self.service.read_property(
                        device_address,
                        device_identifier,
                        "object-list",
                        array_index=i + 1,
                    )
                    object_list.append(object_identifier)

            names_list = []
            for object_identifier in object_list:
                try:
                    property_value = await self.service.read_property(
                        device_address, object_identifier, "object-name"
                    )
                    names_list.append(str(property_value))
                except bacpypes3.errors.InvalidTag as err:
                    names_list.append("ERROR - Invalid Tag")

            return {"object_list": object_list, "names_list": names_list}

        except Exception as e:
            _log.error(f"Unexpected error during point discovery: {e}")
            raise e

    async def read_multiple_properties(self, device_instance: int, requests: list[ReadMultiplePropertiesRequest]):
        # Validate the input using Pydantic wrapper model
        try:
            ReadMultiplePropertiesRequestWrapper(
                device_instance=device_instance,
                requests=requests
            )
        except ValidationError as e:
            raise ValueError(f"Invalid read multiple properties request: {e}")
        
        device_address = await self.get_device_address(device_instance)
        property_requests = [(ObjectIdentifier(req.object_identifier), req.property_identifier) for req in requests]

        try:
            result = await self.service.read_property_multiple(device_address, property_requests)
            return result
        except Exception as e:
            _log.error(f"Exception during read multiple properties: {e}")
            return str(e)

    async def who_is_range(self, start_instance: int, end_instance: int):
        return await self.perform_who_is(start_instance, end_instance)
