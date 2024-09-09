from pydantic import BaseModel, Field, ValidationError, conint, field_validator
from typing import Union, Optional, List
from bacpypes3.primitivedata import PropertyIdentifier, ObjectType
import math

# Utility function to check for NaN or Inf values in floating point numbers
def nan_or_inf_check(encoded_value):
    if isinstance(encoded_value, float):
        if math.isnan(encoded_value):
            return "NaN"
        elif math.isinf(encoded_value):
            return "Inf" if encoded_value > 0 else "-Inf"
    return encoded_value

# Base response model (optional)
class BaseResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

# DeviceInstanceRange model for validating start and end range of device instances
class DeviceInstanceRange(BaseModel):
    start_instance: conint(ge=0, le=4194303) = Field(..., description="The start of the BACnet device instance range.")
    end_instance: conint(ge=0, le=4194303) = Field(..., description="The end of the BACnet device instance range.")

# WritePropertyRequest model for validating write property requests
class WritePropertyRequest(BaseModel):
    device_instance: conint(ge=0, le=4194303) = Field(...)
    object_identifier: str
    property_identifier: str
    value: Union[float, int, str]
    priority: Optional[conint(ge=1, le=16)] = Field(default=None)

    # Validate property identifier (must be a valid BACnet property identifier)
    @field_validator('property_identifier')
    def validate_property_identifier(cls, v):
        valid_property_identifiers = set(PropertyIdentifier._enum_map.keys())
        if v not in valid_property_identifiers:
            raise ValueError(f"property_identifier '{v}' is not a valid BACnet property identifier")
        return v

    # Validate object identifier (must include object type and instance, e.g., "analog-input,1")
    @field_validator('object_identifier')
    def validate_object_identifier(cls, v):
        if ',' not in v:
            raise ValueError("object_identifier must include a type and an instance number separated by a comma")

        object_type, instance_str = v.split(',', 1)
        valid_object_type_identifiers = set(ObjectType._enum_map.keys())
        if object_type not in valid_object_type_identifiers:
            raise ValueError(f"object_identifier '{object_type}' is not a valid BACnet object type")

        try:
            instance_number = int(instance_str)
            if not (0 < instance_number < (1 << 22) - 1):
                raise ValueError("Instance number out of range")
        except ValueError as e:
            raise ValueError(f"Invalid instance number: {e}")

        return v

# ReadMultiplePropertiesRequest model for validating read multiple properties requests
class ReadMultiplePropertiesRequest(BaseModel):
    object_identifier: str
    property_identifier: str

    # Validate object identifier for read multiple properties
    @field_validator('object_identifier')
    def validate_object_identifier(cls, v):
        if ',' not in v:
            raise ValueError("object_identifier must include a type and an instance number separated by a comma")

        object_type, instance_str = v.split(',', 1)
        valid_object_type_identifiers = set(ObjectType._enum_map.keys())
        if object_type not in valid_object_type_identifiers:
            raise ValueError(f"object_identifier '{object_type}' is not a valid BACnet object type")

        try:
            instance_number = int(instance_str)
            if not (0 < instance_number < (1 << 22) - 1):
                raise ValueError("Instance number out of range")
        except ValueError as e:
            raise ValueError(f"Invalid instance number: {e}")

        return v

    # Validate property identifier for read multiple properties
    @field_validator('property_identifier')
    def validate_property_identifier(cls, v):
        valid_property_identifiers = set(PropertyIdentifier._enum_map.keys())
        if v not in valid_property_identifiers:
            raise ValueError(f"property_identifier '{v}' is not a valid BACnet property identifier")
        return v

# Wrapper for read multiple properties request containing the device instance and the list of requests
class ReadMultiplePropertiesRequestWrapper(BaseModel):
    device_instance: conint(ge=0, le=4194303) = Field(...)
    requests: List[ReadMultiplePropertiesRequest]

# DeviceInstanceValidator model for validating a single device instance
class DeviceInstanceValidator(BaseModel):
    device_instance: conint(ge=0, le=4194303) = Field(..., description="The device instance ID like '201201' for example")

    # Validation method for the device instance
    @classmethod
    def validate_instance(cls, device_instance: int):
        try:
            return cls(device_instance=device_instance).device_instance
        except ValidationError as e:
            raise ValueError(f"Invalid device instance: {e}")
