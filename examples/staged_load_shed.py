import asyncio
from easy_aso import EasyASO

"""
$ python examples/staged_load_shed.py --name easy-aso --instance 987654
"""

config_dict = {
    "POWER_MTR_BACNET_ADDR": "10.200.200.233",
    "POWER_MTR_BACNET_OBJ_ID": "analog-input,7",
    "POWER_THRESHOLD": 120.0,
    "SLEEP_INTERVAL_SECONDS": 60,
    "DUTY_CYCLE_INTERVAL_SECONDS": 900,
    "STAGE_UP_DOWN_TIMER": 300,
    "stages": [
        {
            "description": "Stage 1: Reset zone setpoints upward.",
            "bacnet_points": [
                {
                    "address": "10.200.200.233",
                    "bacnet_obj_id": "analog-value,2",
                    "write_value": 78.0,
                    "release_value": "null",
                    "write_priority": 10,
                },
                # Add more points if needed
            ],
        },
        {
            "description": "Stage 2: Turn off non-essential lighting.",
            "bacnet_points": [
                {
                    "address": "10.200.200.233",
                    "bacnet_obj_id": "analog-value,3",
                    "write_value": 50.0,
                    "release_value": "null",
                    "write_priority": 10,
                },
            ],
        },
        {
            "description": "Stage 3: Limit cooling system capacity.",
            "bacnet_points": [
                {
                    "address": "10.200.200.233",
                    "bacnet_obj_id": "analog-output,3",
                    "write_value": 0.0,
                    "release_value": "null",
                    "write_priority": 10,
                },
            ],
        },
    ],
}


async def main():
    await EasyASO().run_load_shed(config_dict)


if __name__ == "__main__":
    asyncio.run(main())
