
from pydantic import BaseModel
from typing import Optional, Union


# Web App model to make POST request for BACnet write
class WritePropertyRequest(BaseModel):
    device_instance: int
    object_identifier: str
    property_identifier: str
    value: Optional[Union[float, int, str]]
    priority: Optional[int] = None


# Web App User authentication model
class User(BaseModel):
    username: str
