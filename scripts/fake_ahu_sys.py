import asyncio
import logging
import random
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.app import Application
from bacpypes3.local.analog import AnalogValueObject, AnalogInputObject
from bacpypes3.local.binary import BinaryInputObject
from bacpypes3.local.cmd import Commandable
from bacpypes3.object import MultiStateValueObject

'''
python fake_ahu_sys.py --name BensFakeAhu --instance 3056672
'''

class CommandableAnalogValueObject(Commandable, AnalogValueObject):
    """Commandable Analog Value Object"""

class CommandableMultiStateValueObject(Commandable, MultiStateValueObject):
    """Commandable Multi-State Value Object"""

class FakeAHUApplication:
    def __init__(self, args):
        self.app = Application.from_args(args)

        # Create BACnet objects (points) for the fake AHU
        self.points = {
            "DAP-P": AnalogInputObject(
                objectIdentifier=("analogInput", 1),
                objectName="DAP-P",
                presentValue=1.0,
                units="inchesOfWater",
                description="AHU Duct Pressure"
            ),
            "SA-T": AnalogInputObject(
                objectIdentifier=("analogInput", 2),
                objectName="SA-T",
                presentValue=75.0,
                units="degreesFahrenheit",
                description="AHU Supply Air Temp"
            ),
            "MA-T": AnalogInputObject(
                objectIdentifier=("analogInput", 3),
                objectName="MA-T",
                presentValue=72.0,
                units="degreesFahrenheit",
                description="AHU Mixed Air Temp"
            ),
            "RA-T": AnalogInputObject(
                objectIdentifier=("analogInput", 4),
                objectName="RA-T",
                presentValue=70.0,
                units="degreesFahrenheit",
                description="AHU Return Air Temp"
            ),
            "SF-S": BinaryInputObject(
                objectIdentifier=("binaryInput", 5),
                objectName="SF-S",
                presentValue="active",
                description="Supply Fan Status"
            ),
            "SA-FLOW": AnalogInputObject(
                objectIdentifier=("analogInput", 6),
                objectName="SA-FLOW",
                presentValue=1000.0,
                units="cubicFeetPerMinute",
                description="Supply Air Flow"
            ),
            "OA-T": AnalogInputObject(
                objectIdentifier=("analogInput", 7),
                objectName="OA-T",
                presentValue=85.0,
                units="degreesFahrenheit",
                description="Outside Air Temperature (Local)"
            ),
            # Commandable points (won't be updated)
            "DAP-SP": CommandableAnalogValueObject(
                objectIdentifier=("analogValue", 8),
                objectName="DAP-SP",
                presentValue=1.0,
                units="inchesOfWater",
                covIncrement=0.1,
                description="AHU Duct Pressure Setpoint"
            ),
            "SF-O": CommandableAnalogValueObject(
                objectIdentifier=("analogOutput", 9),
                objectName="SF-O",
                presentValue=50.0,
                units="percent",
                covIncrement=1.0,
                description="Supply Fan Speed Command"
            ),
            "HTG-O": CommandableAnalogValueObject(
                objectIdentifier=("analogOutput", 10),
                objectName="HTG-O",
                presentValue=0.0,
                units="percent",
                covIncrement=1.0,
                description="Heating Valve Command"
            ),
            "CLG-O": CommandableAnalogValueObject(
                objectIdentifier=("analogOutput", 11),
                objectName="CLG-O",
                presentValue=0.0,
                units="percent",
                covIncrement=1.0,
                description="Cooling Valve Command"
            ),
            "OAT-NETWORK": CommandableAnalogValueObject(
                objectIdentifier=("analogValue", 12),
                objectName="OAT-NETWORK",
                presentValue=85.0,
                units="degreesFahrenheit",
                covIncrement=0.1,
                description="Outside Air Temperature (Network)"
            ),
            "Occ-Schedule": CommandableMultiStateValueObject(
                objectIdentifier=("multiStateValue", 343),
                objectName="Occ-Schedule",
                presentValue=1,  # Start as Occupied
                numberOfStates=4,  # Occupied, UnOccupied, Standby, Not Set
                stateText=["Not Set", "Occupied", "UnOccupied", "Standby"],
                description="Occupancy Schedule"
            )
        }

        # Add all objects to the BACnet application
        for point in self.points.values():
            self.app.add_object(point)

        # Start the task to periodically update the non-commandable points
        asyncio.create_task(self.update_values())

    async def update_values(self):
        """Simulate changing values for the non-commandable AHU points."""
        while True:
            await asyncio.sleep(5.0)
            print("=" * 50)  # Indicator for each loop iteration
            # Update and print all points
            for name, obj in self.points.items():
                if isinstance(obj, AnalogInputObject):
                    new_value = random.uniform(5.0, 95.0)
                    obj.presentValue = new_value
                    print(f"Updated {name}: {new_value}")
                elif isinstance(obj, BinaryInputObject):
                    new_value = random.choice(["active", "inactive"])
                    obj.presentValue = new_value
                    print(f"Updated {name}: {new_value}")
                elif isinstance(obj, (AnalogValueObject, MultiStateValueObject)):
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
