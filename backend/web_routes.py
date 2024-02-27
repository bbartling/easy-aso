from fastapi import FastAPI
from typing import Optional, Union
from pydantic import BaseModel


"""
https://192.168.0.102:8000/bacnet/whois/201201
https://192.168.0.102:8000/bacnet/read/201201/analog-input,2
https://192.168.0.102:8000/bacnet/write/201201/analog-value,300/present-value/99
"""


class WritePropertyRequest(BaseModel):
    device_instance: int
    object_identifier: str
    property_identifier: str
    value: Optional[
        Union[float, int, str]
    ]  # Accepts float, int, or None, and includes str for "null"
    priority: Optional[int] = None


def setup_routes(app: FastAPI, bacnet_app):
    @app.get("/")
    async def hello_world():
        return {"message": "Hello World"}

    @app.get("/bacpypes/config")
    async def bacpypes_config():
        return await bacnet_app.config()

    @app.get("/bacnet/whois/{device_instance}")
    async def bacnet_whois(device_instance):
        return await bacnet_app.who_is(device_instance)

    @app.get("/bacnet/read/{device_instance}/{object_identifier}")
    async def bacnet_read_present_value(device_instance, object_identifier):
        return await bacnet_app.read_present_value(device_instance, object_identifier)

    @app.get("/bacnet/read/{device_instance}/{object_identifier}/{property_identifier}")
    async def bacnet_read_property(
        device_instance, object_identifier, property_identifier
    ):
        return await bacnet_app.read_property(
            device_instance, object_identifier, property_identifier
        )

    @app.post("/bacnet/write")
    async def bacnet_write_property(request: WritePropertyRequest):
        # Extract values from the request object
        device_instance = request.device_instance
        object_identifier = request.object_identifier
        property_identifier = request.property_identifier
        value = request.value
        priority = request.priority

        # Call the write property function with the extracted values
        return await bacnet_app.write_property(
            device_instance, object_identifier, property_identifier, value, priority
        )
