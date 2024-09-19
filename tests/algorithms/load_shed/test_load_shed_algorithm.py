import pytest
import asyncio
from unittest.mock import AsyncMock
import itertools
from easy_aso.algorithms.load_shed.load_shed_algorithm import load_shed


@pytest.mark.asyncio
async def test_load_shed_algorithm():
    # Mock the EasyASO app
    mock_app = AsyncMock()
    mock_app.get_optimization_enabled_status = AsyncMock(return_value=True)
    # Use itertools.cycle to cycle through the mock power readings
    mock_app.do_read = AsyncMock(side_effect=itertools.cycle([150, 150, 110, 110]))
    mock_app.do_write = AsyncMock()

    # Example config dict for testing
    config_dict = {
        "POWER_MTR_BACNET_ADDR": "10.200.200.233",
        "POWER_MTR_BACNET_OBJ_ID": "analog-input,7",
        "POWER_THRESHOLD": 120.0,
        "SLEEP_INTERVAL_SECONDS": 0.01,  # Shorter sleep for faster testing
        "DUTY_CYCLE_INTERVAL_SECONDS": 0.02,
        "STAGE_UP_DOWN_TIMER": 0.01,
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
                    }
                ],
            },
        ],
    }

    # Run the load shedding algorithm with a max_iterations limit
    await asyncio.wait_for(
        load_shed(mock_app, config_dict, max_iterations=5), timeout=5
    )

    # Check if the algorithm initiated and released stages correctly
    assert mock_app.do_write.call_count >= 2
    mock_app.do_write.assert_any_call("10.200.200.233", "analog-value,2", 78.0, 10)
    mock_app.do_write.assert_any_call("10.200.200.233", "analog-value,2", "null", 10)


@pytest.mark.asyncio
async def test_load_shed_three_stages():
    # Mock the EasyASO app
    mock_app = AsyncMock()
    mock_app.get_optimization_enabled_status = AsyncMock(return_value=True)

    # Simulate power readings cycling through different power levels
    mock_app.do_read = AsyncMock(
        side_effect=itertools.cycle([150, 150, 150, 110, 110, 110])
    )

    # No failures, all writes succeed
    mock_app.do_write = AsyncMock()

    # Example config dict for three stages
    config_dict = {
        "POWER_MTR_BACNET_ADDR": "10.200.200.233",
        "POWER_MTR_BACNET_OBJ_ID": "analog-input,7",
        "POWER_THRESHOLD": 120.0,
        "SLEEP_INTERVAL_SECONDS": 0.001,  # Shorter sleep for faster testing
        "DUTY_CYCLE_INTERVAL_SECONDS": 0.002,
        "STAGE_UP_DOWN_TIMER": 0.001,
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
                    }
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
                    }
                ],
            },
            {
                "description": "Stage 3: Limit cooling system capacity.",
                "bacnet_points": [
                    {
                        "address": "10.200.200.233",
                        "bacnet_obj_id": "analog-output,1",
                        "write_value": 25.0,
                        "release_value": "null",
                        "write_priority": 10,
                    }
                ],
            },
        ],
    }

    # Run the load shedding algorithm for a limited time
    await asyncio.wait_for(
        load_shed(mock_app, config_dict, max_iterations=10), timeout=5
    )

    # Print all the calls made to do_write for debugging purposes
    print(mock_app.do_write.call_args_list)

    # Check if the algorithm initiated and released stages correctly
    assert (
        mock_app.do_write.call_count >= 6
    )  # 3 stages, each written to once and released once

    # Verify the calls for each stage were made correctly
    mock_app.do_write.assert_any_call("10.200.200.233", "analog-value,2", 78.0, 10)
    mock_app.do_write.assert_any_call("10.200.200.233", "analog-value,2", "null", 10)
    mock_app.do_write.assert_any_call("10.200.200.233", "analog-value,3", 50.0, 10)
    mock_app.do_write.assert_any_call("10.200.200.233", "analog-value,3", "null", 10)
    mock_app.do_write.assert_any_call("10.200.200.233", "analog-output,1", 25.0, 10)
    mock_app.do_write.assert_any_call("10.200.200.233", "analog-output,1", "null", 10)
