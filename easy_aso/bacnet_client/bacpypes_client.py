from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier, Null
from bacpypes3.apdu import ErrorRejectAbortNack, PropertyReference, PropertyIdentifier, ErrorType
from bacpypes3.constructeddata import AnyAtomic
from bacpypes3.app import Application
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.vendor import get_vendor_info

from .base import BacnetClient


class BacpypesClient(BacnetClient):
    """Direct bacpypes3-backed BACnet client.

    NOTE: This owns the BACnet/IP socket. In the container architecture, only the gateway
    should use this.
    """

    def __init__(self, args=None, argv=None):
        parser = SimpleArgumentParser()
        # allow callers to pass through bacpypes3 args
        if args is not None:
            self.args = args
        elif argv is not None:
            self.args = parser.parse_args(argv)
        else:
            self.args = parser.parse_args()
        self.app: Application | None = None

    async def start(self) -> None:
        self.app = Application.from_args(self.args)

    async def stop(self) -> None:
        # bacpypes3 Application doesn't have a hard "close"; keep placeholder
        self.app = None

    def _addr(self, address: str) -> Address:
        return Address(address)

    def _obj(self, obj_id: str) -> ObjectIdentifier:
        obj_type, inst = obj_id.split(",")
        return ObjectIdentifier((obj_type.strip(), int(inst.strip())))

    def _parse_property_identifier(self, property_identifier: str) -> Tuple[str, Optional[int]]:
        if "," in property_identifier:
            prop_id, prop_index = property_identifier.split(",")
            return prop_id.strip(), int(prop_index.strip())
        return property_identifier, None

    async def read(self, address: str, object_identifier: str, property_identifier: str = "present-value") -> Any:
        assert self.app is not None, "BacpypesClient.start() must be called first"
        try:
            pv = await self.app.read_property(self._addr(address), self._obj(object_identifier), property_identifier)
            if isinstance(pv, AnyAtomic):
                return pv.get_value()
            return pv
        except ErrorRejectAbortNack as e:
            raise RuntimeError(f"BACnet read failed: {e}") from e

    async def write(
        self,
        address: str,
        object_identifier: str,
        value: Any,
        priority: Optional[int] = None,
        property_identifier: str = "present-value",
    ) -> None:
        assert self.app is not None, "BacpypesClient.start() must be called first"

        prop_id, prop_index = self._parse_property_identifier(property_identifier)

        if value == "null":
            if priority is None:
                raise ValueError("null can only be used for overrides with a priority")
            value = Null(())

        try:
            await self.app.write_property(
                self._addr(address),
                self._obj(object_identifier),
                prop_id,
                value,
                prop_index,
                priority if priority is not None else -1,
            )
        except ErrorRejectAbortNack as e:
            raise RuntimeError(f"BACnet write failed: {e}") from e

    async def rpm(self, address: str, *args: str) -> List[Dict[str, Any]]:
        assert self.app is not None, "BacpypesClient.start() must be called first"

        args_list = list(args)
        if not args_list:
            raise ValueError("RPM requires at least an object identifier and one property")

        address_obj = self._addr(address)
        device_info = await self.app.device_info_cache.get_device_info(address_obj)
        vendor_info = get_vendor_info(device_info.vendor_identifier if device_info else 0)

        parameter_list: List[Any] = []
        while args_list:
            obj_id_str = args_list.pop(0)
            object_identifier = vendor_info.object_identifier(obj_id_str)
            object_class = vendor_info.get_object_class(object_identifier[0])
            if not object_class:
                return [{"error": f"Unrecognized object type: {object_identifier}"}]

            parameter_list.append(object_identifier)

            property_reference_list: List[PropertyReference] = []
            while args_list:
                property_reference = PropertyReference(propertyIdentifier=args_list.pop(0), vendor_info=vendor_info)

                if property_reference.propertyIdentifier not in (
                    PropertyIdentifier.all,
                    PropertyIdentifier.required,
                    PropertyIdentifier.optional,
                ):
                    property_type = object_class.get_property_type(property_reference.propertyIdentifier)
                    if not property_type:
                        return [{"error": f"Unrecognized property: {property_reference.propertyIdentifier}"}]

                property_reference_list.append(property_reference)

                if args_list and (":" in args_list[0] or "," in args_list[0]):
                    break

            parameter_list.append(property_reference_list)

        try:
            response = await self.app.read_property_multiple(address_obj, parameter_list)
        except ErrorRejectAbortNack as err:
            return [{"error": f"Error during RPM: {err}"}]

        out: List[Dict[str, Any]] = []
        for (obj_id, prop_id, prop_index, prop_val) in response:
            rec: Dict[str, Any] = {
                "object_identifier": obj_id,
                "property_identifier": prop_id,
                "property_array_index": prop_index,
            }
            if isinstance(prop_val, ErrorType):
                rec["value"] = f"Error: {prop_val.errorClass}, {prop_val.errorCode}"
            else:
                rec["value"] = prop_val
            out.append(rec)
        return out
