#!/usr/bin/env python3
"""
ping_pong_tester.py

JSON-RPC ping-pong tester for the DIY BACnet FastAPI server.

- Uses /client_read_property and /client_write_property
- Talks to fake AHU (instance 3456789) and fake VAV (instance 3456790)
- Designed to be run while tcpdump captures BACnet/IP traffic so you can
  confirm that the server is NOT sending Who-Is every time.

python3 scripts/ping_pong_tester.py \
  --base-url http://192.168.204.12:8080 \
  --loops 20 \
  --sleep 3 \
  --skip-whois


"""

import argparse
import json
import time
from typing import Any, Dict, Optional

import requests

DEFAULT_BASE_URL = "http://192.168.204.12:8080"


def rpc_call(base_url: str, method: str, params: Dict[str, Any], id_: str = "0") -> Dict[str, Any]:
    """
    Generic helper to call a JSON-RPC endpoint on the DIY BACnet server.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": id_,
        "method": method,
        "params": params,
    }
    url = f"{base_url}/{method}"
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data


def client_whois_range_once(base_url: str) -> None:
    """
    Optional: run a whois_range scan once at the start to verify connectivity.
    """
    print("\n=== Running single client_whois_range scan (once) ===")
    params = {
        "request": {
            "start_instance": 1,
            "end_instance": 3456799,
        }
    }
    data = rpc_call(base_url, "client_whois_range", params)
    print(json.dumps(data, indent=2))


def read_property(
    base_url: str,
    device_instance: int,
    object_identifier: str,
    property_identifier: str = "present-value",
) -> Optional[Any]:
    """
    Helper for /client_read_property.

    Returns the raw 'result' JSON; you can adapt this once you know the exact response structure.
    """
    params = {
        "request": {
            "device_instance": device_instance,
            "object_identifier": object_identifier,
            "property_identifier": property_identifier,
        }
    }
    data = rpc_call(base_url, "client_read_property", params)
    result = data.get("result")
    print(f"[READ] device={device_instance}, obj={object_identifier}, prop={property_identifier}")
    print(json.dumps(result, indent=2))
    return result


def write_property(
    base_url: str,
    device_instance: int,
    object_identifier: str,
    value: Any,
    property_identifier: str = "present-value",
    priority: Optional[int] = 8,
) -> Dict[str, Any]:
    """
    Helper for /client_write_property.

    Writes a value at a given priority (default 8).
    """
    request: Dict[str, Any] = {
        "device_instance": device_instance,
        "object_identifier": object_identifier,
        "property_identifier": property_identifier,
        "value": value,
    }
    if priority is not None:
        request["priority"] = priority

    params = {"request": request}
    data = rpc_call(base_url, "client_write_property", params)
    result = data.get("result")
    print(
        f"[WRITE] device={device_instance}, obj={object_identifier}, "
        f"prop={property_identifier}, value={value}, priority={priority}"
    )
    print(json.dumps(result, indent=2))
    return result or {}


def run_ping_pong(
    base_url: str,
    loops: int,
    sleep_seconds: float,
    skip_whois: bool,
) -> None:
    """
    Main driver: repeatedly reads/writes AHU + VAV points.
    """
    # Fake device instances from fake_ahu.py and fake_vav.py
    AHU_INSTANCE = 3456789
    VAV_INSTANCE = 3456790

    # Object IDs used in fake devices:
    # AHU: SAT-SP -> analogValue,2
    AHU_SAT_SP_OID = "analog-value,2"
    # VAV: ZoneTemp -> analogInput,1, ZoneCoolingSpt -> analogValue,1
    VAV_ZONE_TEMP_OID = "analog-input,1"
    VAV_ZONE_COOL_SPT_OID = "analog-value,1"

    if not skip_whois:
        client_whois_range_once(base_url)

    print("\n=== Starting ping-pong loop ===")
    print(f"Base URL: {base_url}")
    print(f"Loops: {loops}, Sleep: {sleep_seconds} seconds\n")

    for i in range(1, loops + 1):
        print(f"\n========== ITERATION {i} ==========")

        # --- VAV: read ZoneTemp, write ZoneCoolingSpt ---
        print("\n--- VAV (Zone1VAV) ---")
        read_property(
            base_url=base_url,
            device_instance=VAV_INSTANCE,
            object_identifier=VAV_ZONE_TEMP_OID,
        )

        # Simple ping-pong: alternate cooling setpoint 71°F / 73°F
        new_vav_sp = 71.0 if i % 2 == 1 else 73.0
        write_property(
            base_url=base_url,
            device_instance=VAV_INSTANCE,
            object_identifier=VAV_ZONE_COOL_SPT_OID,
            value=new_vav_sp,
        )

        # --- AHU: read SAT-SP, then write SAT-SP ---
        print("\n--- AHU (BensFakeAhu) ---")
        read_property(
            base_url=base_url,
            device_instance=AHU_INSTANCE,
            object_identifier=AHU_SAT_SP_OID,
        )

        # Ping-pong SAT-SP between 55°F and 58°F
        new_sat_sp = 55.0 if i % 2 == 1 else 58.0
        write_property(
            base_url=base_url,
            device_instance=AHU_INSTANCE,
            object_identifier=AHU_SAT_SP_OID,
            value=new_sat_sp,
        )

        print(f"\n[ping_pong] Sleeping {sleep_seconds} seconds...\n")
        time.sleep(sleep_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ping-pong tester for DIY BACnet JSON-RPC FastAPI server."
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL of the BACnet FastAPI server (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--loops",
        type=int,
        default=10,
        help="Number of ping-pong iterations (default: 10)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=5.0,
        help="Seconds to sleep between iterations (default: 5.0)",
    )
    parser.add_argument(
        "--skip-whois",
        action="store_true",
        help="Skip the initial client_whois_range scan.",
    )

    args = parser.parse_args()
    run_ping_pong(
        base_url=args.base_url,
        loops=args.loops,
        sleep_seconds=args.sleep,
        skip_whois=args.skip_whois,
    )


if __name__ == "__main__":
    main()
