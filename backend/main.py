from __future__ import annotations

import asyncio
import re
import uvicorn
from contextlib import asynccontextmanager
from typing import Optional, Union

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from bacpypes3.debugging import ModuleLogger
from bacpypes3.argparse import SimpleArgumentParser

from bacpypes3.pdu import Address, GlobalBroadcast
from bacpypes3.primitivedata import Atomic, ObjectIdentifier
from bacpypes3.constructeddata import Sequence, AnyAtomic, Array, List
from bacpypes3.apdu import ErrorRejectAbortNack
from bacpypes3.app import Application
from bacpypes3.primitivedata import Null, CharacterString, ObjectIdentifier

# for serializing the configuration
from bacpypes3.settings import settings
from bacpypes3.json.util import (
    atomic_encode,
    sequence_to_json,
    extendedlist_to_json_list,
)

from bacpypes3.debugging import ModuleLogger
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.app import Application
from bacpypes3.local.analog import AnalogValueObject
from bacpypes3.local.binary import BinaryValueObject
from bacpypes3.local.cmd import Commandable

from web_routes import setup_routes

# python main.py --ssl-certfile /home/bbartling/FreeBAS/backend/certs/certificate.pem --ssl-keyfile /home/bbartling/FreeBAS/backend/certs/private.key


# Set up logging
_debug = 0
_log = ModuleLogger(globals())

# bacnet server update interval
INTERVAL = 1.0


class CommandableAnalogValueObject(Commandable, AnalogValueObject):
    """
    Commandable Analog Value Object
    """


class FreeBasApplication:
    def __init__(
        self,
        args,
        test_bv,
        test_av,
        commandable_analog_value,
        ssl_certfile,
        ssl_keyfile,
    ):
        # embed an application
        self.bacnet_app = Application.from_args(args)

        # extract the kwargs that are special to this application
        self.test_bv = test_bv
        self.bacnet_app.add_object(test_bv)

        self.test_av = test_av
        self.bacnet_app.add_object(test_av)

        self.commandable_analog_value = commandable_analog_value
        self.bacnet_app.add_object(commandable_analog_value)

        self.web_app = FastAPI()
        self.ssl_certfile = ssl_certfile
        self.ssl_keyfile = ssl_keyfile

        # Setup FastAPI routes
        setup_routes(self.web_app, self)

        # create a task to update the values
        asyncio.create_task(self.update_values())

    # for FASTapi web app
    async def start_server(self, host="0.0.0.0", port=8000, log_level="info"):
        config_kwargs = {
            "app": self.web_app,
            "host": host,
            "port": port,
            "log_level": log_level,
        }

        # Add SSL configuration if certfile and keyfile are provided
        if self.ssl_certfile and self.ssl_keyfile:
            config_kwargs["ssl_keyfile"] = self.ssl_keyfile
            config_kwargs["ssl_certfile"] = self.ssl_certfile

        config = uvicorn.Config(**config_kwargs)
        server = uvicorn.Server(config)
        await server.serve()

    # update BACnet server
    async def update_values(self):
        test_values = [
            ("active", 1.0),
            ("inactive", 2.0),
            ("active", 3.0),
            ("inactive", 4.0),
        ]

        while True:
            await asyncio.sleep(INTERVAL)
            next_value = test_values.pop(0)
            test_values.append(next_value)
            if _debug:
                _log.debug("    - next_value: %r", next_value)
                _log.debug(
                    "commandable_analog_value: %r",
                    self.commandable_analog_value.presentValue,
                )

            self.test_av.presentValue = next_value[1]
            self.test_bv.presentValue = next_value[0]

    async def _read_property(
        self, device_instance: int, object_identifier: str, property_identifier: str
    ):
        """
        Read a property from an object.
        """
        _log.debug("_read_property %r %r", device_instance, object_identifier)

        device_address: Address
        device_info = self.bacnet_app.device_info_cache.instance_cache.get(
            device_instance, None
        )
        if device_info:
            device_address = device_info.device_address
            _log.debug("    - cached address: %r", device_address)
        else:
            # returns a list, there should be only one
            i_ams = await self.bacnet_app.who_is(device_instance, device_instance)
            if not i_ams:
                raise HTTPException(
                    status_code=400, detail=f"device not found: {device_instance}"
                )
            if len(i_ams) > 1:
                raise HTTPException(
                    status_code=400, detail=f"multiple devices: {device_instance}"
                )

            device_address = i_ams[0].pduSource
            _log.debug("    - i-am response: %r", device_address)

        try:
            property_value = await self.bacnet_app.read_property(
                device_address, ObjectIdentifier(object_identifier), property_identifier
            )
            if _debug:
                _log.debug("    - property_value: %r", property_value)
        except ErrorRejectAbortNack as err:
            if _debug:
                _log.debug("    - exception: %r", err)
            raise HTTPException(status_code=400, detail=f"error/reject/abort: {err}")

        if isinstance(property_value, AnyAtomic):
            if _debug:
                _log.debug("    - schedule objects")
            property_value = property_value.get_value()

        if isinstance(property_value, Atomic):
            encoded_value = atomic_encode(property_value)
        elif isinstance(property_value, Sequence):
            encoded_value = sequence_to_json(property_value)
        elif isinstance(property_value, (Array, List)):
            encoded_value = extendedlist_to_json_list(property_value)
        else:
            raise HTTPException(
                status_code=400, detail=f"JSON encoding: {property_value}"
            )
        if _debug:
            _log.debug("    - encoded_value: %r", encoded_value)

        return {property_identifier: encoded_value}

    async def _write_property(
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

        # 'property[index]' matching
        property_index_re = re.compile(r"^([A-Za-z-]+)(?:\[([0-9]+)\])?$")

        # split the property identifier and its index
        property_index_match = property_index_re.match(property_identifier)
        if not property_index_match:
            return "property specification incorrect"

        property_identifier, property_array_index = property_index_match.groups()
        if property_array_index is not None:
            property_array_index = int(property_array_index)

        if value == "null":
            if priority is None:
                return "Error, null is only for overrides"
            value = Null(())

        try:
            response = await self.bacnet_app.write_property(
                address,
                object_identifier,
                property_identifier,
                value,
                property_array_index,
                priority,
            )
            if _debug:
                _log.debug("    - response: %r", response)
            return response

        except ErrorRejectAbortNack as err:
            if _debug:
                _log.debug("    - exception: %r", err)
            return str(err)

    async def config(self):
        """
        Return the bacpypes configuration as JSON.
        """
        _log.debug("config")

        object_list = []
        for obj in self.bacnet_app.objectIdentifier.values():
            _log.debug("    - obj: %r", obj)
            object_list.append(sequence_to_json(obj))

        return {"BACpypes": dict(settings), "application": object_list}

    async def who_is(
        self,
        device_instance: Union[int, str],  # Allow both int and str
        address: Optional[str] = None,
    ):
        """
        Send out a Who-Is request and return the I-Am messages.
        """

        # Convert device_instance to int if it's a string
        if isinstance(device_instance, str):
            device_instance = int(device_instance)

        # if the address is None in the who_is() call it defaults to a global
        # broadcast but it's nicer to be explicit here
        destination: Address
        if address:
            destination = Address(address)
        else:
            destination = GlobalBroadcast()
        if _debug:
            _log.debug("    - destination: %r", destination)

        # returns a list, there should be only one
        i_ams = await self.bacnet_app.who_is(
            device_instance, device_instance, destination
        )

        result = []
        for i_am in i_ams:
            if _debug:
                _log.debug("    - i_am: %r", i_am)
            result.append(sequence_to_json(i_am))

        return result

    async def read_present_value(self, device_instance: int, object_identifier: str):
        """
        Read the `present-value` property from an object.
        """
        _log.debug("read_present_value %r %r", device_instance, object_identifier)

        if isinstance(device_instance, str):
            device_instance = int(device_instance)

        return await self._read_property(
            device_instance, object_identifier, "present-value"
        )

    async def read_property(
        self, device_instance: int, object_identifier: str, property_identifier: str
    ):
        """
        Read a property from an object.
        """
        _log.debug("read_present_value %r %r", device_instance, object_identifier)

        if isinstance(device_instance, str):
            device_instance = int(device_instance)

        return await self._read_property(
            device_instance, object_identifier, property_identifier
        )

    async def write_property(
        self,
        device_instance: int,
        object_identifier: str,
        property_identifier: str,
        value: str,
        priority: int = -1,
    ):
        """
        Write a property from an object.
        """

        if isinstance(device_instance, str):
            device_instance = int(device_instance)

        return await self._write_property(
            device_instance, object_identifier, property_identifier, value, priority
        )


async def main():

    parser = SimpleArgumentParser()
    parser.add_argument(
        "--host",
        help="host address for service",
        default="0.0.0.0",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="host address for service",
        default=8000,
    )
    parser.add_argument(
        "--log-level",
        help="logging level",
        default="info",
    )

    parser.add_argument("--ssl-certfile", help="SSL certificate file")
    parser.add_argument("--ssl-keyfile", help="SSL key file")

    args = parser.parse_args()

    if _debug:
        _log.debug("args: %r", args)

    # define BACnet objects
    test_av = AnalogValueObject(
        objectIdentifier=("analogValue", 1),
        objectName="av",
        presentValue=0.0,
        statusFlags=[0, 0, 0, 0],
        covIncrement=1.0,
    )
    _log.debug("    - test_av: %r", test_av)

    test_bv = BinaryValueObject(
        objectIdentifier=("binaryValue", 1),
        objectName="bv",
        presentValue="inactive",
        statusFlags=[0, 0, 0, 0],
    )
    _log.debug("    - test_bv: %r", test_bv)

    # Create an instance of your commandable object
    commandable_analog_value = CommandableAnalogValueObject(
        objectIdentifier=("analogValue", 3),
        objectName="commandable-av",
        presentValue=-1.0,
        statusFlags=[0, 0, 0, 0],
        covIncrement=1.0,
        description="Commandable analog value object",
    )

    # Instantiate the FreeBasApplication with BACnet objects
    sample_app = FreeBasApplication(
        args,
        test_av=test_av,
        test_bv=test_bv,
        commandable_analog_value=commandable_analog_value,
        ssl_certfile=args.ssl_certfile,
        ssl_keyfile=args.ssl_keyfile,
    )

    # Start the web server
    await sample_app.start_server(
        args.host,
        args.port,
        args.log_level,
    )


if __name__ == "__main__":
    asyncio.run(main())
