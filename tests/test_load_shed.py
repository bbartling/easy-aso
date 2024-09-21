import pytest
from easy_aso.algorithms.load_shed.load_shed_algorithm import (
    should_initiate_stage,
    should_release_stage,
)

from unittest.mock import Mock
from unittest.mock import AsyncMock
from easy_aso.algorithms.load_shed.load_shed_algorithm import (
    ConfigError,
    load_shed,
    validate_config,
)


@pytest.mark.parametrize(
    "building_power, power_threshold, time_elapsed, stage_timer_remaining, expected",
    [  # Building power exceeds threshold, time elapsed
        (150, 120, 10, 5, True),
        # Building power below threshold
        (110, 120, 10, 5, False),
        # Time elapsed less than stage_timer_remaining
        (150, 120, 4, 5, False),
        # Time elapsed more than stage_timer_remaining
        (150, 120, 6, 5, True),
    ],
)
def test_should_initiate_stage(
    building_power, power_threshold, time_elapsed, stage_timer_remaining, expected
):
    assert (
        should_initiate_stage(
            building_power, power_threshold, time_elapsed, stage_timer_remaining
        )
        == expected
    )


@pytest.mark.parametrize(
    "building_power, power_threshold, time_elapsed, stage_timer_remaining, expected",
    [  # Building power below threshold, time elapsed
        (110, 120, 10, 5, True),
        # Building power exceeds threshold
        (150, 120, 10, 5, False),
        # Time elapsed less than stage_timer_remaining
        (110, 120, 4, 5, False),
        # Time elapsed more than stage_timer_remaining
        (110, 120, 6, 5, True),
    ],
)
def test_should_release_stage(
    building_power, power_threshold, time_elapsed, stage_timer_remaining, expected
):
    assert (
        should_release_stage(
            building_power, power_threshold, time_elapsed, stage_timer_remaining
        )
        == expected
    )


def test_config_dict_structure():
    config_dict = {
        "POWER_MTR_BACNET_ADDR": "10.200.200.233",
        "POWER_MTR_BACNET_OBJ_ID": "analog-input,7",
        "POWER_THRESHOLD": 120.0,
        "SLEEP_INTERVAL_SECONDS": 0.01,
        "STAGE_UP_TIMER": 0.01,
        "STAGE_DOWN_TIMER": 0.02,
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
        ],
    }

    # Check that config_dict contains the correct number of stages
    assert "stages" in config_dict
    assert len(config_dict["stages"]) == 2

    # Check that each stage has the required fields
    for stage in config_dict["stages"]:
        assert "description" in stage
        assert "bacnet_points" in stage
        for point in stage["bacnet_points"]:
            assert "address" in point
            assert "bacnet_obj_id" in point
            assert "write_value" in point
            assert "release_value" in point
            assert "write_priority" in point


@pytest.mark.asyncio
async def test_opt_status_disable_releases_stages():
    # Mock the EasyASO app
    mock_app = Mock()

    # First, opt_status is True (optimization enabled), then False (optimization disabled)
    mock_app.get_optimization_enabled_status = Mock(side_effect=[True, False])

    # Simulate a building power reading above the threshold to start load shedding
    mock_app.do_read = AsyncMock(return_value=150)

    # Mock do_write to track BACnet writes (for initiating and releasing stages)
    mock_app.do_write = AsyncMock()

    # Example config dict for testing
    config_dict = {
        "POWER_MTR_BACNET_ADDR": "10.200.200.233",
        "POWER_MTR_BACNET_OBJ_ID": "analog-input,7",
        "POWER_THRESHOLD": 120.0,
        "SLEEP_INTERVAL_SECONDS": 0.01,
        "STAGE_UP_TIMER": 0.01,
        "STAGE_DOWN_TIMER": 0.02,
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

    # Run the load shedding algorithm
    await load_shed(mock_app, config_dict, max_iterations=2)

    # Check that both initiation and release were called
    assert mock_app.do_write.call_count == 2  # One initiation, one release

    # Verify the stage initiation call
    mock_app.do_write.assert_any_call(
        "10.200.200.233", "analog-value,2", 78.0, 10
    )  # Stage initiation

    # Verify the stage release call when opt_status became False
    mock_app.do_write.assert_any_call(
        "10.200.200.233", "analog-value,2", "null", 10
    )  # Stage release


def test_validate_config_bad_config():
    # Example of a bad config dict (missing POWER_MTR_BACNET_ADDR and incorrect type for STAGE_DOWN_TIMER)
    bad_config_dict = {
        "POWER_MTR_BACNET_OBJ_ID": "analog-input,7",
        "POWER_THRESHOLD": 120.0,
        "SLEEP_INTERVAL_SECONDS": 0.01,
        "STAGE_UP_TIMER": 0.01,
        "STAGE_DOWN_TIMER": "0.02",  # Incorrect type (string instead of float)
        "stages": [
            {
                "description": "Stage 1: Reset zone setpoints upward.",
                "bacnet_points": [
                    {
                        "bacnet_obj_id": "analog-value,2",
                        "write_value": 78.0,
                        "release_value": "null",
                        "write_priority": 10,
                    }
                ],
            },
        ],
    }

    # Test the validation function directly
    with pytest.raises(
        ConfigError, match="Missing required config key: POWER_MTR_BACNET_ADDR"
    ):
        validate_config(bad_config_dict)
