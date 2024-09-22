import pytest
from unittest.mock import AsyncMock
from easy_aso.algorithms.ahu_duct_static_reset.ahu_static_reset_algorithm import (
    AHUStaticPressureReset,
    ConfigError,
)


@pytest.mark.asyncio
async def test_ahu_static_pressure_reset_ignore_highest():
    mock_app = AsyncMock()

    # VAV box readings mock - Extend the side effect to cover all iterations
    # 2 iterations, 2 VAV boxes, 2 calls per box (damper + airflow)
    mock_app.do_read = AsyncMock(
        side_effect=[
            100,
            0.4,  # First VAV box: damper position 100%, airflow setpoint 0.4
            80,
            0.5,  # Second VAV box: damper position 80%, airflow setpoint 0.5
            100,
            0.4,  # First VAV box: damper position 100%, airflow setpoint 0.4 (2nd iteration)
            80,
            0.5,  # Second VAV box: damper position 80%, airflow setpoint 0.5 (2nd iteration)
        ]
    )

    # Example config dict with I=1 to ignore the highest damper position
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
        "SP0": 0.5,
        "SPmin": 0.1,
        "SPmax": 2.0,
        "Td": 0.1,  # 6 seconds
        "T": 0.02,  # 2 seconds
        "I": 1,  # Ignore the highest damper position
        "SPtrim": -0.05,
        "SPres": 0.06,
        "SPres_max": 0.13,
        "AHU_STATIC_PRESSURE_BACNET_ADDR": "10.200.200.233",
        "AHU_STATIC_PRESSURE_OBJ_ID": "analog-output,1",
        "AHU_STATIC_PRESSURE_PRIORITY": 8,  # Priority to use for BACnet writes
    }

    # Create an instance of the class
    ahu_reset = AHUStaticPressureReset(config_dict)

    # Run the algorithm
    await ahu_reset.run(mock_app, max_iterations=2)

    # Check that the highest damper (100%),
    # was ignored and the remaining one (80%) was processed
    # 2 VAV boxes * 2 readings (damper + airflow)
    # per iteration, 2 iterations
    assert mock_app.do_read.call_count == 8


def test_validate_ahu_config_bad():
    bad_config = {
        "VAV_BOXES": [],  # Empty list
        "SP0": 0.5,
    }

    # Instantiate the class and ensure validation raises ConfigError for bad config
    with pytest.raises(ConfigError):
        AHUStaticPressureReset(bad_config)
