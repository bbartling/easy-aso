import asyncio
import logging
import random
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.app import Application
from bacpypes3.local.analog import (
    AnalogValueObject,
    AnalogInputObject,
    AnalogOutputObject,
)
from bacpypes3.local.binary import BinaryInputObject, BinaryOutputObject
from bacpypes3.local.cmd import Commandable
from bacpypes3.object import MultiStateValueObject  # Import for multi-state
from bacpypes3.primitivedata import Enumerated  # For multi-state-like behavior

"""
$ python fake_ahu_sys.py --name BensFakeAhu --instance 3456789
"""

UPDATE_INTERVAL_SECONDS = 20


class CommandableAnalogValueObject(Commandable, AnalogValueObject):
    """Commandable Analog Value Object"""


class CommandableMultiStateValueObject(Commandable, MultiStateValueObject):
    """Commandable Multi-State Value Object"""


class FakeAHUApplication:
    def __init__(self, args):
        self.app = Application.from_args(args)

        # Create BACnet objects (points) for the fake AHU
        self.points = {
            # Analog Inputs
            "DAP-P": AnalogInputObject(
                objectIdentifier=("analogInput", 1),
                objectName="DAP-P",
                presentValue=1.0,
                units="inchesOfWater",
                description="AHU Duct Pressure",
            ),
            "SA-T": AnalogInputObject(
                objectIdentifier=("analogInput", 2),
                objectName="SA-T",
                presentValue=75.0,
                units="degreesFahrenheit",
                description="AHU Supply Air Temp",
            ),
            "MA-T": AnalogInputObject(
                objectIdentifier=("analogInput", 3),
                objectName="MA-T",
                presentValue=72.0,
                units="degreesFahrenheit",
                description="AHU Mixed Air Temp",
            ),
            "RA-T": AnalogInputObject(
                objectIdentifier=("analogInput", 4),
                objectName="RA-T",
                presentValue=70.0,
                units="degreesFahrenheit",
                description="AHU Return Air Temp",
            ),
            "SA-FLOW": AnalogInputObject(
                objectIdentifier=("analogInput", 5),
                objectName="SA-FLOW",
                presentValue=1000.0,
                units="cubicFeetPerMinute",
                description="Supply Air Flow",
            ),
            "OA-T": AnalogInputObject(
                objectIdentifier=("analogInput", 6),
                objectName="OA-T",
                presentValue=85.0,
                units="degreesFahrenheit",
                description="Outside Air Temperature (Local)",
            ),
            # Building electrical power
            "ELEC-PWR": AnalogInputObject(
                objectIdentifier=("analogInput", 7),
                objectName="ELEC-PWR",
                presentValue=150.0,  # Initial value
                units="kilowatts",
                description="Building Electrical Power",
            ),
            # VAV Zone Analog Inputs
            **{
                f"VAV-{i}-ZN-T": AnalogInputObject(
                    objectIdentifier=("analogInput", 7 + i * 2 - 1),
                    objectName=f"VAV-{i}-ZN-T",
                    presentValue=75.0,
                    units="degreesFahrenheit",
                    description=f"VAV {i} Zone Air Temperature",
                )
                for i in range(1, 6)
            },
            **{
                f"VAV-{i}-DPR-O": AnalogInputObject(
                    objectIdentifier=("analogInput", 7 + i * 2),
                    objectName=f"VAV-{i}-DPR-O",
                    presentValue=50.0,
                    units="percent",
                    description=f"VAV {i} Air Damper Position",
                )
                for i in range(1, 6)
            },
            # Analog Outputs
            "SF-O": CommandableAnalogValueObject(
                objectIdentifier=("analogOutput", 1),
                objectName="SF-O",
                presentValue=50.0,
                units="percent",
                covIncrement=1.0,
                description="Supply Fan Speed Command",
            ),
            "HTG-O": CommandableAnalogValueObject(
                objectIdentifier=("analogOutput", 2),
                objectName="HTG-O",
                presentValue=0.0,
                units="percent",
                covIncrement=1.0,
                description="Heating Valve Command",
            ),
            "CLG-O": CommandableAnalogValueObject(
                objectIdentifier=("analogOutput", 3),
                objectName="CLG-O",
                presentValue=0.0,
                units="percent",
                covIncrement=1.0,
                description="Cooling Valve Command",
            ),
            # Analog Values
            "DAP-SP": CommandableAnalogValueObject(
                objectIdentifier=("analogValue", 1),
                objectName="DAP-SP",
                presentValue=1.0,
                units="inchesOfWater",
                covIncrement=0.1,
                description="AHU Duct Pressure Setpoint",
            ),
            "OAT-NETWORK": CommandableAnalogValueObject(
                objectIdentifier=("analogValue", 2),
                objectName="OAT-NETWORK",
                presentValue=85.0,
                units="degreesFahrenheit",
                covIncrement=0.1,
                description="Outside Air Temperature (Network)",
            ),
            # VAV Zone Setpoints
            **{
                f"VAV-{i}-ZN-SP": CommandableAnalogValueObject(
                    objectIdentifier=("analogValue", 2 + i),
                    objectName=f"VAV-{i}-ZN-SP",
                    presentValue=75.0,  # Default setpoint
                    units="degreesFahrenheit",
                    covIncrement=0.5,
                    description=f"VAV {i} Zone Air Temperature Setpoint",
                )
                for i in range(1, 6)
            },
            # Binary Inputs
            "SF-S": BinaryInputObject(
                objectIdentifier=("binaryInput", 1),
                objectName="SF-S",
                presentValue="active",
                description="Supply Fan Status",
            ),
            # Binary Outputs
            "SF-C": BinaryOutputObject(
                objectIdentifier=("binaryOutput", 1),
                objectName="SF-C",
                presentValue="inactive",  # Initial state
                description="Supply Fan Command",
            ),
            # Multi-State Values
            "Occ-Schedule": CommandableMultiStateValueObject(
                objectIdentifier=("multiStateValue", 1),
                objectName="Occ-Schedule",
                presentValue=1,  # Start as Occupied
                numberOfStates=4,  # Occupied, UnOccupied, Standby, Not Set
                stateText=["Not Set", "Occupied", "UnOccupied", "Standby"],
                description="Occupancy Schedule",
            ),
        }

        # Add all objects to the BACnet application
        for point in self.points.values():
            self.app.add_object(point)

        # Start the task to periodically update the non-commandable points
        asyncio.create_task(self.update_values())

    async def update_values(self):
        """Simulate changing values for the non-commandable AHU points."""
        while True:
            await asyncio.sleep(UPDATE_INTERVAL_SECONDS)
            print("=" * 50)  # Indicator for each loop iteration
            # Update and print all points
            for name, obj in self.points.items():
                if isinstance(obj, AnalogInputObject):
                    # Update specific points with different ranges
                    if name == "ELEC-PWR":
                        new_value = random.uniform(100.0, 300.0)
                    elif "ZN-T" in name:
                        new_value = random.uniform(60.0, 80.0)
                    elif "DPR-O" in name:
                        new_value = random.uniform(0.0, 100.0)
                    else:
                        new_value = random.uniform(5.0, 95.0)

                    obj.presentValue = new_value
                    print(f"Updated {name}: {new_value}")
                elif isinstance(obj, BinaryInputObject):
                    new_value = random.choice(["active", "inactive"])
                    obj.presentValue = new_value
                    print(f"Updated {name}: {new_value}")
                elif isinstance(
                    obj, (AnalogValueObject, MultiStateValueObject, BinaryOutputObject)
                ):
                    # Print the commandable objects as well
                    print(f"{name}: {obj.presentValue}")


async def main():
    args = SimpleArgumentParser().parse_args()
    logging.info("args: %r", args)

    # Instantiate the application
    app = FakeAHUApplication(args)

    # Run the BACnet server until interrupted
    await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("BACnet AHU simulation stopped.")
