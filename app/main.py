from __future__ import annotations

from app.config import setup_logging

# Set up application-wide logging configuration at the very beginning
setup_logging()

import asyncio
import re
import logging
import time
import datetime
import random
import os
import json
from typing import Optional, Union

from fastapi import FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
import secrets

from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.pdu import Address, GlobalBroadcast
from bacpypes3.primitivedata import Atomic, ObjectIdentifier
from bacpypes3.constructeddata import Sequence, AnyAtomic, Array, List
from bacpypes3.apdu import ErrorRejectAbortNack
from bacpypes3.app import Application
from bacpypes3.primitivedata import Null, ObjectIdentifier

# for serializing the configuration
from bacpypes3.settings import settings
from bacpypes3.json.util import (
    atomic_encode,
    sequence_to_json,
    extendedlist_to_json_list,
)

from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.app import Application
from bacpypes3.local.analog import AnalogValueObject
from bacpypes3.local.binary import BinaryValueObject

from app.routes.web_routes import setup_routes


# $ python main.py --tls


# Set up logging
_debug = 0

# Create a logger for this module
_log = logging.getLogger(__name__)

# bacnet server update GLOBAL_VAR_UPDATE_INTERVAL
GLOBAL_VAR_UPDATE_INTERVAL = 1.0


class FreeBasApplication:
    def __init__(self, args, building_occ, outside_air_temp, use_tls=False):
        # embed an application
        self.bacnet_app = Application.from_args(args)

        # extract the kwargs that are special to this application
        self.building_occ = building_occ
        self.bacnet_app.add_object(building_occ)

        self.outside_air_temp = outside_air_temp
        self.bacnet_app.add_object(outside_air_temp)
        
        # BACnet global vars for BAS
        self.global_vars_last_update_time = 0
        self.global_vars_update_interval = 60
        self.global_current_outside_temperature = -555.
        self.global_occupied_bool = False

        self.web_app = FastAPI()

        # Conditional TLS setup
        if use_tls:
            certs_dir = os.path.join(os.path.dirname(__file__), "..", "certs")
            self.ssl_certfile = os.path.join(certs_dir, "certificate.pem")
            self.ssl_keyfile = os.path.join(certs_dir, "private.key")
        else:
            self.ssl_certfile = None
            self.ssl_keyfile = None

        self.days_of_week = []
        self.time_slots = []
        self.default_schedule = {}

        # Generates a 32-byte (256-bit) URL-safe secret key
        secret_key = secrets.token_urlsafe(32)

        self.web_app.add_middleware(SessionMiddleware, secret_key=secret_key)

        self.web_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allows all origins
            allow_credentials=True,
            allow_methods=["*"],  # Allows all methods
            allow_headers=["*"],  # Allows all headers
        )

        self.web_app.mount(
            "/static", StaticFiles(directory="app/static"), name="static"
        )
        self.templates = Jinja2Templates(directory="app/templates")

        # Load the default schedule and user setup
        self.initialize_schedule()
        self.users = {"admin": {"username": "admin", "password": "admin"}}

        # OAuth2 setup
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

        # Setup FastAPI routes and additional functionalities
        setup_routes(self.web_app, self)

        # Add user authentication and schedule loading functions here
        self.in_memory_schedule = self.load_schedule()

        # create a task to update the values of the BACnet server
        asyncio.create_task(self.check_global_vars())
        

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
            config_kwargs["ssl_certfile"] = self.ssl_certfile
            config_kwargs["ssl_keyfile"] = self.ssl_keyfile

        config = uvicorn.Config(**config_kwargs)
        server = uvicorn.Server(config)
        await server.serve()

    def initialize_schedule(self):
        # Define days of the week
        self.days_of_week = [
            "Sunday",
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
        ]

        # Define time slots for a 24-hour day
        self.time_slots = [f"{hour:02d}:00" for hour in range(24)]

        # Load the default schedule with 7 AM to 5 PM for Monday to Friday
        self.default_schedule = {
            day: {"start": "07:00", "end": "17:00"}
            if day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            else {"start": None, "end": None}
            for day in self.days_of_week
        }

        return self

    def load_schedule(self):
        """Load the schedule from the JSON file into the cache."""
        try:
            # Adjust the path since schedule.json is in the project root, not in a config directory
            schedule_path = os.path.join(
                os.path.dirname(__file__), "..", "schedule.json"
            )
            with open(schedule_path, "r") as file:
                schedule = json.load(file)
                _log.debug("Schedule loaded: \n", schedule)
                return schedule
        except FileNotFoundError:
            _log.error("Error loading default schedule!")
            return {}  # Or return an empty dict
        
    def save_schedule(self, schedule_data):
        """Load the schedule from the JSON file into the cache."""
        try:
            # Adjusted path to point to the root directory
            schedule_path = os.path.join(
                os.path.dirname(__file__), "..", "schedule.json"
            )
            with open(schedule_path, "w") as file:
                json.dump(schedule_data, file, indent=4)
            _log.debug("Schedule successfully updated and saved.")
        except Exception as e:
            # Handle potential errors, perhaps logging them or notifying an admin
            _log.error(f"Failed to save the updated schedule: {e}")


    async def check_global_vars(self):
        while True:
            await asyncio.sleep(GLOBAL_VAR_UPDATE_INTERVAL)

            try:
                # Check occupancy status
                occ_status = await self.check_occupancy_status()
                current_occ_bool = occ_status["is_occupied"]

                # Compare with the previous state and update only if different
                if current_occ_bool != self.global_occupied_bool:
                    # State has changed, update global tracking variable
                    self.global_occupied_bool = current_occ_bool

                    # Convert boolean to string as required by your server
                    occ_str = "active" if current_occ_bool else "inactive"
                    
                    # Update bacpypes3 bacnet server value
                    self.building_occ.presentValue = occ_str

            except Exception as e:
                _log.error(f"Error checking occupancy status: {e}")

            try:
                await self.update_outside_air_temp()
            except Exception as e:
                _log.error(f"Error getting outside air temperature: {e}")


    async def update_outside_air_temp(self):
        current_time = time.time()

        # Check if more than 60 seconds have passed since the last update
        if current_time - self.global_vars_last_update_time > self.global_vars_update_interval:
            
            await asyncio.sleep(0.01) # simulate API call
            current_temperature = random.uniform(50, 100)

            # Check if the temperature change is greater than 0.1 degrees
            if abs(current_temperature - self.global_current_outside_temperature) > 0.1:
                self.global_vars_last_update_time = current_time
                self.global_current_outside_temperature = current_temperature
                
                # update bacpypes3 bacnet server value
                self.outside_air_temp.presentValue = current_temperature


    async def check_occupancy_status(self):
        now = datetime.datetime.now()
        current_day = now.strftime("%A")
        current_time = now.strftime("%H:%M")
        todays_schedule = self.in_memory_schedule.get(current_day, {"start": None, "end": None})

        is_occupied = False
        if todays_schedule["start"] and todays_schedule["end"]:
            is_occupied = todays_schedule["start"] <= current_time < todays_schedule["end"]
        
        return {
            "current_time": current_time,
            "current_day": current_day,
            "is_occupied": is_occupied,
            "schedule": todays_schedule,
        }


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
        "--host", help="Host address for the service", default="0.0.0.0"
    )
    parser.add_argument("--port", type=int, help="Port for the service", default=8000)
    parser.add_argument("--log-level", help="Logging level", default="info")
    parser.add_argument(
        "--tls",
        action="store_true",
        help="Enable TLS by using SSL cert and key from the certs directory",
    )

    args = parser.parse_args()

    if _debug:
        _log.debug("args: %r", args)

    # define BACnet objects
    outside_air_temp = AnalogValueObject(
        objectIdentifier=("analogValue", 1),
        objectName="Outside_Air_Temp_Sensor",
        presentValue=0.0,
        statusFlags=[0, 0, 0, 0],
        covIncrement=1.0,
    )
    _log.debug("    - outside_air_temp: %r", outside_air_temp)

    building_occ = BinaryValueObject(
        objectIdentifier=("binaryValue", 1),
        objectName="Occupied",
        presentValue="inactive",
        statusFlags=[0, 0, 0, 0],
    )
    _log.debug("    - building_occ: %r", building_occ)


    # Instantiate the FreeBasApplication with BACnet objects and TLS flag
    sample_app = FreeBasApplication(
        args,
        outside_air_temp=outside_air_temp,
        building_occ=building_occ,
        use_tls=args.tls,  # Pass the TLS flag directly
    )

    # Start the web server with host, port, and log level from command-line arguments
    await sample_app.start_server(
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    asyncio.run(main())