from pydantic import (
    RootModel,
    BaseModel,
    StrictBool,
    conint,
    confloat,
    conint,
    Field,
    ValidationError,
    field_validator,
)
from typing import Dict, Union, Optional, List

from bacpypes3.primitivedata import PropertyIdentifier, ObjectType
from fastapi import HTTPException
import math


class PointUpdate(
    RootModel[Dict[str, Union[conint(strict=True), confloat(strict=True), StrictBool]]]
):
    pass


def nan_or_inf_check(encoded_value):
    if isinstance(encoded_value, float):
        if math.isnan(encoded_value):
            return "NaN"
        elif math.isinf(encoded_value):
            return "Inf" if encoded_value > 0 else "-Inf"
    return encoded_value


class BaseResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


class PriorityArrayResponse(BaseModel):
    priority_level: int
    type: str
    value: Union[str, float, None]


class SupervisorySummary(BaseModel):
    device_id: int
    address: Optional[str]
    points: List[dict]  # You could break this into another Pydantic model if desired
    summary: Dict[str, int]


class DeviceInstanceOnly(BaseModel):
    device_instance: conint(ge=0, le=4194303) = Field(
        ..., description="Single BACnet device instance (0–4194303)"
    )

    class Config:
        json_schema_extra = {"example": {"device_instance": 987654}}


class DeviceInstanceRange(BaseModel):
    start_instance: conint(ge=0, le=4194303) = Field(
        ..., description="Start of the instance scan range"
    )
    end_instance: conint(ge=0, le=4194303) = Field(
        ..., description="End of the instance scan range"
    )

    class Config:
        json_schema_extra = {"example": {"start_instance": 1000, "end_instance": 1010}}


class DeviceInstanceValidator(BaseModel):
    device_instance: conint(ge=0, le=4194303)

    @classmethod
    def validate_instance(cls, device_instance: int):
        try:
            return cls(device_instance=device_instance).device_instance
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=e.errors())


class WritePropertyRequest(BaseModel):
    device_instance: conint(ge=0, le=4194303) = Field(
        ..., description="BACnet device instance (0-4194303)"
    )
    object_identifier: str = Field(
        ..., description="Object ID in the format 'objectType,instanceNumber'"
    )
    property_identifier: str = Field(
        ..., description="BACnet property name like 'present-value'"
    )
    value: Union[float, int, str] = Field(
        ..., description="Value to write, use 'null' (as string) to release override"
    )
    priority: Optional[conint(ge=1, le=16)] = Field(
        default=None,
        description="Priority slot (1-16), required if releasing with 'null'",
    )

    @field_validator("property_identifier")
    @classmethod
    def validate_property_identifier(cls, v):
        valid = set(PropertyIdentifier._enum_map.keys())
        if v not in valid:
            raise ValueError(f"Invalid property_identifier: {v}")
        return v

    @field_validator("object_identifier")
    @classmethod
    def validate_object_identifier(cls, v):
        if "," not in v:
            raise ValueError("Must be in the format objectType,instanceNumber")
        object_type, instance_str = v.split(",", 1)
        if object_type not in ObjectType._enum_map:
            raise ValueError(f"Invalid object type: {object_type}")
        try:
            instance = int(instance_str)
            if not (0 <= instance <= 4194303):
                raise ValueError("Instance out of range")
        except Exception:
            raise ValueError("Instance number must be integer")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "device_instance": 987654,
                "object_identifier": "analog-output,1",
                "property_identifier": "present-value",
                "value": "null",
                "priority": 1,
            }
        }


class ReadMultiplePropertiesRequest(BaseModel):
    object_identifier: str = Field(
        ..., description="BACnet object in the format 'objectType,instanceNumber'"
    )
    property_identifier: str = Field(
        ..., description="BACnet property name like 'present-value'"
    )

    @field_validator("object_identifier")
    @classmethod
    def validate_object_identifier(cls, v):
        if "," not in v:
            raise ValueError("Must be in the format objectType,instanceNumber")
        object_type, instance_str = v.split(",", 1)
        if object_type not in ObjectType._enum_map:
            raise ValueError(f"Invalid object type: {object_type}")
        try:
            int(instance_str)
        except Exception:
            raise ValueError("Instance number must be integer")
        return v

    @field_validator("property_identifier")
    @classmethod
    def validate_property_identifier(cls, v):
        if v not in PropertyIdentifier._enum_map:
            raise ValueError(f"Invalid property identifier: {v}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "object_identifier": "analog-input,2",
                "property_identifier": "present-value",
            }
        }


class ReadMultiplePropertiesRequestWrapper(BaseModel):
    device_instance: conint(ge=0, le=4194303) = Field(
        ..., description="BACnet device instance (0-4194303)"
    )
    requests: List[ReadMultiplePropertiesRequest]

    class Config:
        json_schema_extra = {
            "example": {
                "device_instance": 123456,
                "requests": [
                    {
                        "object_identifier": "analog-input,2",
                        "property_identifier": "present-value",
                    },
                    {
                        "object_identifier": "binary-output,3",
                        "property_identifier": "status-flags",
                    },
                ],
            }
        }


class SingleReadRequest(BaseModel):
    device_instance: conint(ge=0, le=4194303) = Field(
        ..., description="Target device instance"
    )
    object_identifier: str = Field(..., description="e.g., 'analog-output,1'")
    property_identifier: str = Field(
        default="present-value", description="e.g., 'present-value'"
    )

    @field_validator("object_identifier")
    @classmethod
    def validate_object_identifier(cls, v):
        if "," not in v:
            raise ValueError("Must be in the format objectType,instanceNumber")
        object_type, instance_str = v.split(",", 1)
        if object_type not in ObjectType._enum_map:
            raise ValueError(f"Invalid object type: {object_type}")
        try:
            int(instance_str)
        except Exception:
            raise ValueError("Instance number must be integer")
        return v

    @field_validator("property_identifier")
    @classmethod
    def validate_property_identifier(cls, v):
        if v not in PropertyIdentifier._enum_map:
            raise ValueError(f"Invalid property identifier: {v}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "device_instance": 987654,
                "object_identifier": "analog-output,1",
                "property_identifier": "present-value",
            }
        }


class ReadPriorityArrayRequest(BaseModel):
    device_instance: conint(ge=0, le=4194303) = Field(
        ..., description="BACnet device instance"
    )
    object_identifier: str = Field(
        ..., description="Object ID in the format 'objectType,instanceNumber'"
    )

    @field_validator("object_identifier")
    @classmethod
    def validate_object_identifier(cls, v):
        if "," not in v:
            raise ValueError("Must be in the format objectType,instanceNumber")
        object_type, instance_str = v.split(",", 1)
        if object_type not in ObjectType._enum_map:
            raise ValueError(f"Invalid object type: {object_type}")
        try:
            int(instance_str)
        except Exception:
            raise ValueError("Instance number must be an integer")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "device_instance": 987654,
                "object_identifier": "analog-output,1",
            }
        }
