import asyncio
from easy_aso import EasyASO


"""
G36 AHU duct static pressure reset
Dont use a make over coming soon
"""


# Example config dict for the AHU static pressure reset algorithm
config_dict = {
    "VAV_BOXES": [
        {
            "address": "10.200.200.101",
            "damper_obj_id": "analog-input,1",
            "airflow_setpoint_obj_id": "analog-input,2",
        },
        {
            "address": "10.200.200.102",
            "damper_obj_id": "analog-input,1",
            "airflow_setpoint_obj_id": "analog-input,2",
        },
    ],
    "SP0": 0.5,  # Initial static pressure setpoint (inches WC)
    "SPmin": 0.1,  # Minimum static pressure (inches WC)
    "SPmax": 2.0,  # Maximum static pressure (inches WC)
    "Td": 0.1,  # Startup delay (minutes)
    "T": 0.02,  # Adjustment period (minutes)
    "I": 1,  # Ignore the highest damper position
    "SPtrim": -0.05,  # Static pressure trim amount (inches WC)
    "SPres": 0.06,  # Static pressure response amount (inches WC)
    "SPres_max": 0.13,  # Maximum static pressure response increase (inches WC)
    "AHU_STATIC_PRESSURE_BACNET_ADDR": "10.200.200.233",  # BACnet address of the AHU
    "AHU_STATIC_PRESSURE_OBJ_ID": "analog-output,1",  # Object ID for static pressure control
    "AHU_STATIC_PRESSURE_PRIORITY": 8,  # BACnet write priority for pressure changes
}


async def main():
    # Create an EasyASO instance to handle the application and BACnet
    app = EasyASO()

    # Run the AHU static pressure reset algorithm
    await ahu_static_pressure_reset(app, config_dict, max_iterations=5)


if __name__ == "__main__":
    asyncio.run(main())
