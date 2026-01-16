# bacnet_loader.py
import os
import glob
import csv
import logging
from typing import Dict
from difflib import get_close_matches

from bacpypes3.local.analog import AnalogValueObject
from bacpypes3.local.binary import BinaryValueObject
from bacpypes3.local.cmd import Commandable
from bacpypes3.local.object import Object
from bacpypes3.primitivedata import Real
from bacpypes3.basetypes import EngineeringUnits


logger = logging.getLogger("loader")

# used to prevent writeable points from getting updated interally
commandable_point_names: set[str] = set()

point_map: Dict[str, Object] = {}


class CommandableAnalogValueObject(Commandable, AnalogValueObject):
    """Commandable Analog Value Object"""


class CommandableBinaryValueObject(Commandable, BinaryValueObject):
    """Commandable Binary Value Object"""


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
csv_files = glob.glob(os.path.join(ROOT_DIR, "*.csv"))
if len(csv_files) != 1:
    raise FileNotFoundError(
        f"Expected exactly one CSV file in {ROOT_DIR}, found: {csv_files}"
    )
CSV_FILE = csv_files[0]
logger.info(f"Detected CSV file: {CSV_FILE}")

UNIT_NAME_TO_ENUM = {
    name: getattr(EngineeringUnits, name)
    for name in dir(EngineeringUnits)
    if not name.startswith("_") and isinstance(getattr(EngineeringUnits, name), int)
}


def resolve_unit(unit_str):
    if not unit_str or unit_str.strip().lower() in {"null", "none", ""}:
        return EngineeringUnits.noUnits
    unit_str_clean = unit_str.replace(" ", "").replace("_", "").lower()
    normalized_keys = {
        name: name.replace(" ", "").replace("_", "").lower()
        for name in UNIT_NAME_TO_ENUM
    }
    matches = get_close_matches(
        unit_str_clean, normalized_keys.values(), n=1, cutoff=0.6
    )
    if matches:
        best_match_key = [k for k, v in normalized_keys.items() if v == matches[0]][0]
        return UNIT_NAME_TO_ENUM[best_match_key]
    return EngineeringUnits.noUnits


async def load_csv_and_create_objects(app):
    # Added "Default" to the allowed headers logic (optional check)
    required_headers = {"Name", "PointType", "Units", "Commandable"}
    
    with open(CSV_FILE, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        headers = set(reader.fieldnames or [])
        missing_headers = required_headers - headers
        if missing_headers:
            raise ValueError(f"CSV missing required columns: {missing_headers}")

        av_instance_id = 1
        bv_instance_id = 1

        for idx, row in enumerate(reader, start=2):
            try:
                name = row["Name"].strip()
                point_type = row.get("PointType", "").strip().upper()
                unit_str = row.get("Units", "").strip()
                commandable = row.get("Commandable", "").strip().upper() == "Y"
                
                # --- NEW LOGIC: Parse Default Value ---
                default_val_str = row.get("Default", "").strip()
                
                # Default logic will apply if the column exists and isn't empty
                # Otherwise, it falls back to 0.0 or "inactive"
                
                if not name or point_type not in {"AV", "BV"}:
                    logger.warning(f"Skipping invalid row {idx}: {row}")
                    continue

                engineering_unit = resolve_unit(unit_str)

                if point_type == "AV":
                    # Parse float for Analog, default to 0.0 if missing/invalid
                    try:
                        initial_value = float(default_val_str) if default_val_str else 0.0
                    except ValueError:
                        logger.warning(f"Row {idx}: Invalid AV default '{default_val_str}', using 0.0")
                        initial_value = 0.0

                    obj = (
                        CommandableAnalogValueObject
                        if commandable
                        else AnalogValueObject
                    )(
                        objectIdentifier=("analogValue", av_instance_id),
                        objectName=name,
                        presentValue=Real(initial_value),  # <--- UPDATED
                        # For commandable points, relinquishing defaults often falls back to this
                        relinquishDefault=Real(initial_value) if commandable else None,
                        statusFlags=[0, 0, 0, 0],
                        covIncrement=1.0,
                        units=engineering_unit,
                        description=f"RPC-Updatable Analog Value from CSV",
                    )
                    av_instance_id += 1

                elif point_type == "BV":
                    # Parse boolean-ish string for Binary
                    is_active = default_val_str.lower() in {"true", "active", "1", "y", "yes", "on"}
                    initial_value = "active" if is_active else "inactive"

                    # If the column was empty, strictly default to inactive (or keep logic above)
                    if not default_val_str: 
                        initial_value = "inactive"

                    obj = (
                        CommandableBinaryValueObject
                        if commandable
                        else BinaryValueObject
                    )(
                        objectIdentifier=("binaryValue", bv_instance_id),
                        objectName=name,
                        presentValue=initial_value, # <--- UPDATED
                        relinquishDefault=initial_value if commandable else None,
                        statusFlags=[0, 0, 0, 0],
                        description=f"RPC-Updatable Binary Value from CSV",
                    )

                    bv_instance_id += 1

                app.add_object(obj)
                point_map[name] = obj
                logger.debug(
                    f"Added {point_type} {name} (Cmd={commandable}) val={initial_value}"
                )

                if commandable:
                    commandable_point_names.add(name)

            except Exception as e:
                logger.error(f"Failed to create object from row {idx}: {e}")
