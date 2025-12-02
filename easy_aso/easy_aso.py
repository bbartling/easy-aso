"""
Legacy EasyASO base class using bacpypes3.

This module provides a backwards‑compatible implementation of the
``EasyASO`` abstract base class that relies on the `bacpypes3`
library for BACnet communication.  It subclasses the modern
:class:`easy_aso.agent.Agent` so that code written against the
original API continues to work while still participating in the new
agent framework.

The class defines the lifecycle hooks ``on_start``, ``on_step`` and
``on_stop``, which subclasses must implement.  The :meth:`run`
method sets up signal handlers, creates a BACnet application and
dispatches to the subclass lifecycle.  Additional convenience
methods are provided for reading and writing BACnet properties using
bacpypes3, with graceful degradation when the library is not
available.

If ``bacpypes3`` cannot be imported, stub classes are used so that
unit tests can import this module without requiring the library to
be installed.  BACnet operations will be no‑ops in this case.
"""

from __future__ import annotations

import asyncio
import signal
from abc import ABC, abstractmethod
from typing import Any, List, Optional

from .agent import Agent

# Attempt to import bacpypes3.  If unavailable, define lightweight
# stub classes so this module can be imported without the library.
try:
    from bacpypes3.pdu import Address  # type: ignore
    from bacpypes3.primitivedata import ObjectIdentifier, Null  # type: ignore
    from bacpypes3.apdu import (  # type: ignore
        ErrorRejectAbortNack,
        PropertyReference,
        PropertyIdentifier,
        ErrorType,
    )
    from bacpypes3.constructeddata import AnyAtomic  # type: ignore
    from bacpypes3.app import Application  # type: ignore
    from bacpypes3.argparse import SimpleArgumentParser  # type: ignore
    from bacpypes3.local.cmd import Commandable  # type: ignore
    from bacpypes3.local.binary import BinaryValueObject  # type: ignore
    from bacpypes3.vendor import get_vendor_info  # type: ignore
except Exception:
    # Define minimal stubs to allow tests to import this module without
    # bacpypes3.  These stubs provide just enough structure to avoid
    # NameError at import time.  The BACnet methods will be no‑ops.
    class Address(str):
        pass

    class ObjectIdentifier(tuple):
        pass

    class Null:
        def __init__(self, value: Any) -> None:
            self.value = value

    class ErrorRejectAbortNack(Exception):
        pass

    class PropertyReference:
        def __init__(self, propertyIdentifier: Any, vendor_info: Any = None) -> None:
            self.propertyIdentifier = propertyIdentifier

    class PropertyIdentifier:
        # Provide sentinel members used in rpm parsing
        all = required = optional = "all"

    class ErrorType(Exception):
        def __init__(self, errorClass: Optional[Any] = None, errorCode: Optional[Any] = None) -> None:
            self.errorClass = errorClass
            self.errorCode = errorCode

    class AnyAtomic:
        def __init__(self, value: Any = None) -> None:
            self._value = value

        def get_value(self) -> Any:
            return self._value

    class Application:
        """Minimal stub application with async methods returning None."""

        @classmethod
        def from_args(cls, args: Any) -> "Application":
            return cls()

        async def read_property(self, *args: Any, **kwargs: Any) -> Any:
            return None

        async def write_property(self, *args: Any, **kwargs: Any) -> Any:
            return None

        async def read_property_multiple(self, *args: Any, **kwargs: Any) -> List[Any]:
            return []

        class device_info_cache:
            async def get_device_info(self, *args: Any, **kwargs: Any) -> Any:
                return None

    class SimpleArgumentParser:
        def __init__(self) -> None:
            pass

        def add_argument(self, *args: Any, **kwargs: Any) -> None:
            pass

        def parse_args(self) -> Any:
            # Return an object with a no_bacnet_server attribute
            return type("Args", (), {"no_bacnet_server": False})()

    class Commandable:
        pass

    class BinaryValueObject:
        def __init__(self, **kwargs: Any) -> None:
            self.presentValue = kwargs.get("presentValue", "active")

    def get_vendor_info(vendor_id: Any) -> Any:
        class VendorInfo:
            def object_identifier(self, obj: Any) -> Any:
                return obj

            def get_object_class(self, obj_type: Any) -> Any:
                class ObjectClass:
                    def get_property_type(self, pid: Any) -> str:
                        return "unknown"

                return ObjectClass()

        return VendorInfo()


class CommandableBinaryValueObject(Commandable, BinaryValueObject):
    """Concrete commandable binary value object combining two mixins."""

    pass


class EasyASO(Agent, ABC):  # type: ignore
    """Abstract base class for easy‑aso applications using bacpypes3.

    Subclasses must implement ``on_start``, ``on_step`` and ``on_stop``.  The
    base class handles argument parsing, BACnet application creation and
    signal handling.  It also provides convenience methods for reading
    and writing BACnet properties using the underlying application.
    """

    def __init__(self, *args: Any, update_interval: float = 60.0, **kwargs: Any) -> None:
        # Initialise Agent base class with the update interval
        super().__init__(update_interval=update_interval)
        # Parse command line arguments if not supplied
        parser = SimpleArgumentParser()
        parser.add_argument(
            "--no-bacnet-server",
            action="store_true",
            help="Disable the BACnet server functionality",
        )
        # When running under unittest or other frameworks, sys.argv may
        # contain unrelated arguments (e.g. ``discover`` and ``-v``).  Passing
        # such arguments into the bacpypes argument parser can raise
        # unhandled exceptions.  To avoid this we explicitly parse an empty
        # argument list when no explicit ``args`` are provided.  If callers
        # supply an ``args`` object it will be used directly.
        if args:
            # ``args`` may be a sequence where the first element is the
            # namespace from argparse; mirror the behaviour of the old API.
            self.args = args[0]
        else:
            # Parse no command‑line arguments to ignore extraneous sys.argv.
            # Some bacpypes3 versions accept a list argument to ``parse_args``
            # whereas the local stub does not.  Attempt to pass an empty
            # argument list and fall back to a no‑argument call if needed.
            try:
                self.args = parser.parse_args([])
            except TypeError:
                # The stub ``parse_args`` defined when bacpypes3 is absent
                # does not accept arguments.
                self.args = parser.parse_args()
        self.stop_event = asyncio.Event()
        self._stop_handler_called: bool = False
        # Determine whether to enable the BACnet server
        self.no_bacnet_server = getattr(self.args, "no_bacnet_server", False)
        # Create a commandable binary value object representing the kill switch
        self.optimization_enabled_bv = CommandableBinaryValueObject(
            objectIdentifier=("binaryValue", 1),
            objectName="optimization-enabled",
            presentValue="active",
            statusFlags=[0, 0, 0, 0],
            description="Commandable binary value object",
        )
        # Placeholder for the bacpypes application
        self.app: Optional[Application] = None

    @abstractmethod
    async def on_start(self) -> None:
        """Hook called before stepping begins.  Subclasses must override."""
        raise NotImplementedError

    @abstractmethod
    async def on_step(self) -> None:
        """Hook called repeatedly at the update interval.  Subclasses must override."""
        raise NotImplementedError

    @abstractmethod
    async def on_stop(self) -> None:
        """Hook called when the application is stopping.  Subclasses must override."""
        raise NotImplementedError

    # Provide on_update alias for backwards compatibility
    async def on_update(self) -> None:
        await self.on_step()

    def get_optimization_enabled_status(self) -> bool:
        """Return the optimization enabled status from the binary value object."""
        return bool(self.optimization_enabled_bv.presentValue)

    async def create_application(self) -> None:
        """Instantiate the bacpypes Application and register the binary value object."""
        self.app = Application.from_args(self.args)
        if not self.no_bacnet_server and self.app is not None:
            self.app.add_object(self.optimization_enabled_bv)  # type: ignore[attr-defined]

    async def update_server(self) -> None:
        """Simulate server updates on a one‑second interval.  Override if needed."""
        while True:
            await asyncio.sleep(1)

    async def run_lifecycle(self) -> None:
        """Run the subclass lifecycle: on_start -> repeated on_step -> on_stop."""
        try:
            await self.on_start()
            while not self.stop_event.is_set():
                await self.on_step()
                await asyncio.sleep(self.update_interval)
        except asyncio.CancelledError:
            # Graceful cancellation
            pass
        finally:
            await self.on_stop()

    async def stop_handler(self) -> None:
        """Handle external stop signals by setting the stop event and cleaning up."""
        if self._stop_handler_called:
            return
        self._stop_handler_called = True
        self.stop_event.set()
        await self.on_stop()
        # Cancel all tasks except the current one
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()

    async def run(self) -> None:
        """Create the BACnet application, register signal handlers and run the lifecycle."""
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda sig=sig: asyncio.create_task(self.stop_handler()))
        await self.create_application()
        main_task = asyncio.gather(self.update_server(), self.run_lifecycle())
        try:
            await main_task
        except asyncio.CancelledError:
            pass
        finally:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(sig)
            if not self._stop_handler_called:
                await self.on_stop()

    # -------------------------------------------------------------------------
    # BACnet helper functions
    # -------------------------------------------------------------------------
    def _convert_to_address(self, address: str) -> Address:
        """Convert a string to a bacpypes Address object."""
        return Address(address)

    def _convert_to_object_identifier(self, obj_id: str) -> ObjectIdentifier:
        """Convert a string to a bacpypes ObjectIdentifier."""
        object_type, instance_number = obj_id.split(",")
        return ObjectIdentifier((object_type.strip(), int(instance_number.strip())))

    def parse_property_identifier(self, property_identifier: str) -> tuple[str, Optional[int]]:
        """Parse a property identifier that may include an array index."""
        if "," in property_identifier:
            prop_id, prop_index = property_identifier.split(",")
            return prop_id.strip(), int(prop_index.strip())
        return property_identifier, None

    async def bacnet_read(self, address: str, object_identifier: str, property_identifier: str = "present-value") -> Any:
        """Read a BACnet property using the underlying application."""
        if self.app is None:
            return None
        try:
            address_obj = self._convert_to_address(address)
            object_id_obj = self._convert_to_object_identifier(object_identifier)
            property_value = await self.app.read_property(address_obj, object_id_obj, property_identifier)  # type: ignore[attr-defined]
            if isinstance(property_value, AnyAtomic):
                return property_value.get_value()
            return property_value
        except ErrorRejectAbortNack:
            return None
        except Exception:
            return None

    async def bacnet_write(
        self,
        address: str,
        object_identifier: str,
        value: Any,
        priority: int = -1,
        property_identifier: str = "present-value",
    ) -> None:
        """Write a BACnet property using the underlying application."""
        if self.app is None:
            return
        try:
            address_obj = self._convert_to_address(address)
            object_id_obj = self._convert_to_object_identifier(object_identifier)
            property_identifier, property_array_index = self.parse_property_identifier(property_identifier)
            # Handle 'null' values for release
            if value == "null":
                if priority is None:
                    raise ValueError("null can only be used for overrides with a priority")
                value = Null(())
            await self.app.write_property(
                address_obj,
                object_id_obj,
                property_identifier,
                value,
                property_array_index,
                priority,
            )  # type: ignore[attr-defined]
        except ErrorRejectAbortNack:
            pass
        except Exception:
            pass

    async def bacnet_rpm(self, address: str, *args: str) -> List[dict[str, Any]]:
        """Perform a Read Property Multiple request and return a list of results."""
        if self.app is None:
            return []
        args_list: List[str] = list(args)
        address_obj = self._convert_to_address(address)
        device_info = await self.app.device_info_cache.get_device_info(address_obj)  # type: ignore[attr-defined]
        vendor_info = get_vendor_info(device_info.vendor_identifier if device_info else 0)
        parameter_list: List[Any] = []
        while args_list:
            obj_id_str = args_list.pop(0)
            object_identifier = vendor_info.object_identifier(obj_id_str)
            object_class = vendor_info.get_object_class(object_identifier[0])
            if not object_class:
                return [{"error": f"Unrecognized object type: {object_identifier}"}]
            parameter_list.append(object_identifier)
            property_reference_list = []
            while args_list:
                property_reference = PropertyReference(
                    propertyIdentifier=args_list.pop(0), vendor_info=vendor_info
                )
                if property_reference.propertyIdentifier not in (
                    PropertyIdentifier.all,
                    PropertyIdentifier.required,
                    PropertyIdentifier.optional,
                ):
                    property_type = object_class.get_property_type(property_reference.propertyIdentifier)  # type: ignore[call-arg]
                    if not property_type:
                        return [
                            {
                                "error": f"Unrecognized property: {property_reference.propertyIdentifier}",
                            }
                        ]
                property_reference_list.append(property_reference)
                # Break if the next item looks like an object identifier
                if args_list and (":" in args_list[0] or "," in args_list[0]):
                    break
            parameter_list.append(property_reference_list)
        if not parameter_list:
            return [{"error": "Object identifier expected."}]
        try:
            response = await self.app.read_property_multiple(address_obj, parameter_list)  # type: ignore[attr-defined]
        except ErrorRejectAbortNack as err:
            return [{"error": f"Error during RPM: {err}"}]
        result_list: List[dict[str, Any]] = []
        for (obj_id, prop_id, prop_index, prop_value) in response:
            result: dict[str, Any] = {
                "object_identifier": obj_id,
                "property_identifier": prop_id,
                "property_array_index": prop_index,
            }
            if isinstance(prop_value, ErrorType):
                result["value"] = f"Error: {prop_value.errorClass}, {prop_value.errorCode}"
            else:
                result["value"] = prop_value
            result_list.append(result)
        return result_list


__all__ = ["EasyASO"]