from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    name: str
    driver_type: str = Field(description="stub | bacnet_jsonrpc")
    device_address: str
    rpc_base_url: Optional[str] = None
    rpc_entrypoint: Optional[str] = None
    scrape_interval_seconds: float = Field(default=5.0, ge=0.5, le=3600.0)
    enabled: bool = False


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    driver_type: Optional[str] = None
    device_address: Optional[str] = None
    rpc_base_url: Optional[str] = None
    rpc_entrypoint: Optional[str] = None
    scrape_interval_seconds: Optional[float] = None
    enabled: Optional[bool] = None


class PointCreate(BaseModel):
    name: str = ""
    object_identifier: str
    property_identifier: str = "present-value"
    enabled: bool = True


class PointUpdate(BaseModel):
    name: Optional[str] = None
    object_identifier: Optional[str] = None
    property_identifier: Optional[str] = None
    enabled: Optional[bool] = None


class DeviceHealthOut(BaseModel):
    device_id: str
    status: str
    last_poll_at: Optional[str] = None
    last_error: Optional[str] = None


class PointLatestOut(BaseModel):
    point_id: str
    device_id: str
    name: str
    object_identifier: str
    property_identifier: str
    enabled: bool
    last_value: Any = None
    last_polled_at: Optional[str] = None
    last_error: Optional[str] = None
