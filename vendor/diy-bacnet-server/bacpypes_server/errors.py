import fastapi_jsonrpc as jsonrpc
from fastapi_jsonrpc import BaseError
from pydantic import BaseModel
from typing import Optional


class DeviceNotFoundError(jsonrpc.BaseError):
    CODE = 1001
    MESSAGE = "BACnet device not found"

    class DataModel(BaseModel):
        instance: int
        detail: str


class WhoIsFailureError(BaseError):
    CODE = 1002
    MESSAGE = "Who-Is scan failed"

    class DataModel(BaseModel):
        detail: str


class PriorityArrayError(BaseError):
    CODE = 1003
    MESSAGE = "Priority array read failed"

    class DataModel(BaseModel):
        object_identifier: Optional[str] = None
        detail: str


class ReadPropertyError(BaseError):
    CODE = 1004
    MESSAGE = "Failed to read property"

    class DataModel(BaseModel):
        object_identifier: str
        detail: str


class WritePropertyError(BaseError):
    CODE = 1005
    MESSAGE = "Failed to write property"

    class DataModel(BaseModel):
        object_identifier: str
        detail: str


class RPMError(BaseError):
    CODE = 1006
    MESSAGE = "Read Property Multiple failed"

    class DataModel(BaseModel):
        detail: str


class PointDiscoveryError(BaseError):
    CODE = 1007
    MESSAGE = "Failed to discover BACnet points"

    class DataModel(BaseModel):
        instance: int
        detail: str


class SupervisoryCheckError(BaseError):
    CODE = 1008
    MESSAGE = "Supervisory logic check failed"

    class DataModel(BaseModel):
        instance: int
        detail: str
