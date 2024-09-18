import pytest
import asyncio
from unittest.mock import AsyncMock
from easy_aso.algorithms.load_shed.load_shed_algorithm import load_shed

@pytest.mark.asyncio
async def test_load_shed_algorithm():
    # Mock the EasyASO app
    mock_app = AsyncMock()
    mock_app.get_optimization_enabled_status = AsyncMock(return_value=True)
    mock_app.do_read = AsyncMock(side_effect=[150, 150, 110, 110])  # Simulate power readings
    mock_app.do_write = AsyncMock()

    # Example config dict for testing
    config_dict = {
        "POWER_MTR_BACNET_ADDR": "10.200.200.233",
        "POWER_MTR_BACNET_OBJ_ID": "analog-input,7",
        "POWER_THRESHOLD": 120.0,
        "SLEEP_INTERVAL_SECONDS": 1,  # Shorter sleep for testing
        "DUTY_CYCLE_INTERVAL_SECONDS": 2,
        "STAGE_UP_DOWN_TIMER": 1,
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

    # Run the load shedding algorithm for a short period
    await asyncio.wait_for(load_shed(mock_app, config_dict), timeout=5)

    # Check if the algorithm initiated and released stages correctly
    assert mock_app.do_write.call_count >= 2
    mock_app.do_write.assert_any_call(
        "10.200.200.233", "analog-value,2", 78.0, 10
    )
    mock_app.do_write.assert_any_call(
        "10.200.200.233", "analog-value,2", "null", 10
    )
