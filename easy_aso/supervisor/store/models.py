from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(slots=True)
class Device:
    id: str
    name: str
    driver_type: str
    device_address: str
    rpc_base_url: Optional[str]
    rpc_entrypoint: Optional[str]
    scrape_interval_seconds: float
    enabled: bool
    created_at: str
    updated_at: str


@dataclass(slots=True)
class Point:
    id: str
    device_id: str
    name: str
    object_identifier: str
    property_identifier: str
    enabled: bool
    last_value_json: Optional[str]
    last_polled_at: Optional[str]
    last_error: Optional[str]
    created_at: str
    updated_at: str

    def decoded_value(self) -> Any:
        if self.last_value_json is None:
            return None
        import json

        try:
            return json.loads(self.last_value_json)
        except json.JSONDecodeError:
            return self.last_value_json
