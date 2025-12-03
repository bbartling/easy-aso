#!/usr/bin/env python

"""
BACnet Auto-Scan to CSV (Dynamic Priority-Array Detection)
=========================================================

Batch scanner built on bacpypes3 that:

- Sends a single Who-Is over a device instance range.
- For each responding device:
    - Reads object-list
    - Reads object-name for each object
    - Reads present-value (if available)
    - ALWAYS *tries* to read priority-array:
        * If the device supports it, all levels are dumped.
        * If not, the error is caught and ignored.
- Prints all data to stdout (CSV-style).
- Optionally writes one CSV per device to an output directory if --output-dir is given.

Example usage:

    # Auto-detect local address, scan device instances 1–100, print only
    python bacnet_autoscan.py --low-instance 1 --high-instance 100 --output-dir autoscan_csv

    # If you need to specify unique UDP port run with these args
    python bacnet_autoscan.py --address 10.200.200.233/24:47808 \
        --low-instance 1 --high-instance 500 --output-dir autoscan_csv

Requires:
    pip install bacpypes3 ifaddr
"""

import asyncio
import csv
import logging
import os
from typing import Any, List, Optional, Tuple

import bacpypes3
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.app import Application
from bacpypes3.apdu import AbortPDU, AbortReason, ErrorRejectAbortNack
from bacpypes3.constructeddata import AnyAtomic
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier
from bacpypes3.vendor import get_vendor_info

# Global application instance
app: Optional[Application] = None

log = logging.getLogger(__name__)


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

async def discover_points_for_device(
    device_address: Address,
    device_identifier: ObjectIdentifier,
) -> Tuple[List[ObjectIdentifier], List[str]]:
    """
    Given a device address + device identifier (from Who-Is),
    read object-list and object-name for each object.

    Returns:
        (object_list, names_list) aligned 1:1.
    """
    assert app is not None

    # Try to get vendor info if possible (best-effort, fine if None)
    vendor_info = None
    try:
        device_info = await app.device_info_cache.get_device_info(device_address)
        if device_info:
            vendor_info = get_vendor_info(device_info.vendor_identifier)
    except Exception:
        vendor_info = None

    object_list: List[ObjectIdentifier] = []
    names_list: List[str] = []

    log.info("Reading object-list from device %s at %s", device_identifier, device_address)

    # Try reading object-list directly (as an array)
    try:
        object_list = await app.read_property(
            device_address, device_identifier, "object-list"
        )
        log.info(
            "Successfully read object-list from %s (%d objects)",
            device_identifier,
            len(object_list) if object_list else 0,
        )
    except AbortPDU as err:
        if err.apduAbortRejectReason != AbortReason.segmentationNotSupported:
            log.warning("Error reading object-list for %s: %s", device_identifier, err)
            return [], []
    except ErrorRejectAbortNack as err:
        log.warning("Error/reject reading object-list for %s: %s", device_identifier, err)
        return [], []

    # Fallback: read length + element-by-element
    if not object_list:
        try:
            object_list_length = await app.read_property(
                device_address, device_identifier, "object-list", array_index=0
            )
            log.info("Object-list length for %s: %s", device_identifier, object_list_length)

            for i in range(object_list_length):
                obj_id = await app.read_property(
                    device_address,
                    device_identifier,
                    "object-list",
                    array_index=i + 1,
                )
                object_list.append(obj_id)

        except ErrorRejectAbortNack as err:
            log.warning(
                "Error/reject reading object-list length for %s: %s",
                device_identifier,
                err,
            )
            return [], []

    # Now read object-name for each object
    for object_identifier in object_list:
        obj_type = object_identifier[0]
        if vendor_info is not None:
            object_class = vendor_info.get_object_class(obj_type)
            if object_class is None:
                log.info("Unknown object type for %s, skipping", object_identifier)
                continue

        try:
            property_value = await app.read_property(
                device_address, object_identifier, "object-name"
            )
            names_list.append(str(property_value))
        except bacpypes3.errors.InvalidTag as err:  # type: ignore[attr-defined]
            log.warning(
                "Invalid tag error on point %s. Using placeholder name. %s",
                object_identifier,
                err,
            )
            names_list.append("ERROR - Invalid object-name tag")
        except ErrorRejectAbortNack as err:
            log.warning(
                "Error/reject reading object-name for %s: %s", object_identifier, err
            )
            names_list.append("ERROR - object-name read failed")

    return object_list, names_list


async def read_present_value(
    address: Address, object_identifier: ObjectIdentifier
) -> Optional[Any]:
    """
    Read present-value of an object, returning Python-native value if possible.
    """
    assert app is not None
    try:
        value = await app.read_property(
            address, object_identifier, "present-value"
        )
    except ErrorRejectAbortNack as err:
        log.debug("No present-value for %s: %s", object_identifier, err)
        return None
    except Exception as err:
        log.debug("Error reading present-value for %s: %s", object_identifier, err)
        return None

    if isinstance(value, AnyAtomic):
        return value.get_value()
    return value


async def read_priority_array(
    address: Address, object_identifier: ObjectIdentifier
) -> Optional[List[dict]]:
    """
    Read priority-array for an object, if supported.

    Returns:
        List of dicts:
            {
                "level": int,
                "type": str,
                "value": Python/native or raw,
            }
        or None if unsupported/error.
    """
    assert app is not None
    try:
        response = await app.read_property(
            address, object_identifier, "priority-array"
        )
    except ErrorRejectAbortNack as err:
        # Device or object doesn't support this property – that's fine, just skip.
        log.debug("priority-array not supported for %s: %s", object_identifier, err)
        return None
    except Exception as err:
        log.debug(
            "Unexpected error reading priority-array for %s: %s",
            object_identifier,
            err,
        )
        return None

    if not response:
        return None

    parsed: List[dict] = []

    for index, priority_value in enumerate(response):
        if priority_value is None:
            parsed.append(
                {"level": index + 1, "type": "null", "value": None}
            )
            continue

        value_type = getattr(priority_value, "_choice", None)
        value = getattr(priority_value, value_type, None) if value_type else None

        if isinstance(value, AnyAtomic):
            value = value.get_value()

        parsed.append(
            {
                "level": index + 1,  # 1-based priority level
                "type": value_type or "unknown",
                "value": value,
            }
        )

    return parsed


# ------------------------------------------------------------
# Main scanning logic
# ------------------------------------------------------------

async def scan_devices_to_csv(
    low_instance: int,
    high_instance: int,
    output_dir: Optional[str],
) -> None:
    """
    Scan the BACnet network for devices in [low_instance, high_instance].

    Behavior:
      - Single Who-Is(low, high)
      - For each I-Am:
          * discover points
          * read PV
          * always TRY priority-array, skip quietly if unsupported
      - ALWAYS print CSV-style rows to stdout
      - IF output_dir is not None:
          * write one CSV per device into that directory
    """
    assert app is not None

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    log.info(
        "Sending Who-Is with low_instance=%s, high_instance=%s",
        low_instance,
        high_instance,
    )

    # ONE Who-Is call for the whole range
    i_ams = await app.who_is(low_instance, high_instance)

    if not i_ams:
        log.warning("No I-Am responses for range %s–%s", low_instance, high_instance)
        return

    log.info("Received %d I-Am responses", len(i_ams))

    header = [
        "device_id",
        "device_address",
        "object_type",
        "object_instance",
        "object_name",
        "property",
        "priority_level",
        "value_type",
        "value_repr",
    ]

    for i_am in i_ams:
        device_address: Address = i_am.pduSource
        device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier
        instance_id = device_identifier[1]

        # Extra sanity check
        if instance_id < low_instance or instance_id > high_instance:
            log.info(
                "Skipping device %s outside requested range %s–%s",
                device_identifier,
                low_instance,
                high_instance,
            )
            continue

        log.info("=" * 60)
        log.info("Scanning device %s at %s", device_identifier, device_address)

        object_list, names_list = await discover_points_for_device(
            device_address, device_identifier
        )

        if not object_list:
            log.info("No objects discovered for device %s, skipping", device_identifier)
            continue

        rows: List[List[Any]] = []

        for object_identifier, object_name in zip(object_list, names_list):
            obj_type_enum, obj_inst = object_identifier
            if hasattr(obj_type_enum, "name"):
                obj_type_name = obj_type_enum.name
            else:
                obj_type_name = str(obj_type_enum)

            # --- Present Value row ---
            pv = await read_present_value(device_address, object_identifier)
            rows.append(
                [
                    instance_id,                 # device_id
                    str(device_address),        # device_address
                    obj_type_name,              # object_type
                    obj_inst,                   # object_instance
                    object_name,                # object_name
                    "present-value",            # property
                    "",                         # priority_level (blank for PV)
                    "",                         # value_type
                    "" if pv is None else str(pv),  # value_repr
                ]
            )

            # --- Priority Array rows (try for EVERYTHING, skip if unsupported) ---
            pa = await read_priority_array(device_address, object_identifier)
            if pa:
                for entry in pa:
                    rows.append(
                        [
                            instance_id,
                            str(device_address),
                            obj_type_name,
                            obj_inst,
                            object_name,
                            "priority-array",
                            entry["level"],
                            entry["type"],
                            "" if entry["value"] is None else str(entry["value"]),
                        ]
                    )

        if not rows:
            log.info("No data rows for device %s, skipping", device_identifier)
            continue

        # ---- ALWAYS print to stdout ----
        print("")
        print(f"=== Device {device_identifier} @ {device_address} ===")
        print(",".join(header))
        for row in rows:
            print(",".join("" if v is None else str(v) for v in row))

        # ---- Optionally write CSV file ----
        if output_dir:
            csv_path = os.path.join(output_dir, f"device_{instance_id}.csv")
            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(rows)

            log.info(
                "Wrote %d rows for device %s (%s) to %s",
                len(rows),
                device_identifier,
                device_address,
                csv_path,
            )


# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------

async def async_main() -> None:
    global app

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = SimpleArgumentParser()
    parser.add_argument(
        "--low-instance",
        type=int,
        required=True,
        help="Lowest BACnet device instance to query (inclusive).",
    )
    parser.add_argument(
        "--high-instance",
        type=int,
        required=True,
        help="Highest BACnet device instance to query (inclusive).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help=(
            "Directory to place per-device CSV files. "
            "If omitted, results are only printed to stdout."
        ),
    )

    args = parser.parse_args()
    log.info("Arguments: %r", args)

    try:
        # Build the BACnet application stack from args (address, debug, etc.)
        app = Application.from_args(args)
        log.info("BACpypes3 Application created: %r", app)

        await scan_devices_to_csv(
            low_instance=args.low_instance,
            high_instance=args.high_instance,
            output_dir=args.output_dir,
        )

    finally:
        if app is not None:
            app.close()
            log.info("Application closed")


if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        log.info("Keyboard interrupt, exiting.")
