import asyncio


class ConfigError(Exception):
    """Custom exception for invalid configuration"""

    pass


def validate_config(config_dict):
    """Validate config dictionary for required keys and correct data types"""
    required_keys = {
        "POWER_MTR_BACNET_ADDR": str,
        "POWER_MTR_BACNET_OBJ_ID": str,
        "POWER_THRESHOLD": (int, float),
        "SLEEP_INTERVAL_SECONDS": (int, float),
        "STAGE_UP_TIMER": (int, float),
        "STAGE_DOWN_TIMER": (int, float),
        "stages": list,
    }

    # Validate that each required key exists and has the correct type
    for key, expected_type in required_keys.items():
        if key not in config_dict:
            raise ConfigError(f"Missing required config key: {key}")
        if not isinstance(config_dict[key], expected_type):
            raise ConfigError(
                f"Incorrect type for {key}. Expected {expected_type}, got {type(config_dict[key])}"
            )

    # Validate each stage in the stages list
    for i, stage in enumerate(config_dict["stages"], 1):
        if not isinstance(stage, dict):
            raise ConfigError(f"Stage {i} must be a dictionary, got {type(stage)}")

        # Each stage must have 'description' and 'bacnet_points'
        if "description" not in stage or "bacnet_points" not in stage:
            raise ConfigError(
                f"Stage {i} is missing required keys 'description' or 'bacnet_points'"
            )

        if not isinstance(stage["bacnet_points"], list):
            raise ConfigError(
                f"'bacnet_points' in stage {i} must be a list, got {type(stage['bacnet_points'])}"
            )

        # Validate each bacnet_point in the stage
        for point in stage["bacnet_points"]:
            for key in [
                "address",
                "bacnet_obj_id",
                "write_value",
                "release_value",
                "write_priority",
            ]:
                if key not in point:
                    raise ConfigError(f"Missing {key} in bacnet_point of stage {i}")
                if key == "write_priority" and not isinstance(point[key], int):
                    raise ConfigError(
                        f"'write_priority' in bacnet_point of stage {i} must be an integer"
                    )
                # Ensure address and bacnet_obj_id are strings
                if key in ["address", "bacnet_obj_id"] and not isinstance(
                    point[key], str
                ):
                    raise ConfigError(
                        f"'{key}' in bacnet_point of stage {i} must be a string"
                    )


def should_initiate_stage(
    building_power, power_threshold, time_elapsed, stage_timer_remaining
):
    """Determine whether a new stage should be initiated based on the building power and timer."""
    return building_power > power_threshold and time_elapsed >= stage_timer_remaining


def should_release_stage(
    building_power, power_threshold, time_elapsed, stage_timer_remaining
):
    """Determine whether a stage should be released based on the building power and timer."""
    return building_power <= power_threshold and time_elapsed >= stage_timer_remaining


async def load_shed(app, config_dict, max_iterations=None):
    try:
        validate_config(config_dict)
    except ConfigError as e:
        print(f"Configuration Error: {e}")
        raise

    last_operation_time = 0
    current_stage = 0
    iterations = 0
    stages = config_dict.get("stages", [])
    sleep_interval_seconds = config_dict.get("SLEEP_INTERVAL_SECONDS", 60)
    stage_up_timer = config_dict.get("STAGE_UP_TIMER", 300)  # Separate up timer
    stage_down_timer = config_dict.get("STAGE_DOWN_TIMER", 300)  # Separate down timer
    power_threshold = config_dict.get("POWER_THRESHOLD", 120.0)
    power_meter_bacnet_addr = config_dict.get("POWER_MTR_BACNET_ADDR")
    power_meter_bacnet_obj_id = config_dict.get("POWER_MTR_BACNET_OBJ_ID")

    while True:
        if max_iterations is not None and iterations >= max_iterations:
            break

        # Check if optimization is enabled
        opt_status = app.get_optimization_enabled_status()

        if not opt_status:
            # If optimization is disabled, release all active stages and exit
            print("Optimization disabled, releasing all active stages.")
            while current_stage > 0:
                await release_stage(app, stages[current_stage - 1])
                current_stage -= 1
            print("All stages released, exiting load shed.")
            break  # Exit the load_shed algorithm

        # Continue with normal load shedding if optimization is enabled
        building_power = await app.do_read(
            power_meter_bacnet_addr, power_meter_bacnet_obj_id
        )

        current_time = asyncio.get_event_loop().time()
        time_elapsed = current_time - last_operation_time
        up_timer_remaining = max(0, stage_up_timer - time_elapsed)
        down_timer_remaining = max(0, stage_down_timer - time_elapsed)

        # Check to initiate a new stage
        if should_initiate_stage(
            building_power, power_threshold, time_elapsed, up_timer_remaining
        ):
            if current_stage < len(stages):
                current_stage += 1
                last_operation_time = current_time
                await initiate_stage(app, stages[current_stage - 1])

        # Check to release a stage
        if should_release_stage(
            building_power, power_threshold, time_elapsed, down_timer_remaining
        ):
            if current_stage > 0:
                await release_stage(app, stages[current_stage - 1])
                current_stage -= 1
                last_operation_time = current_time

        iterations += 1
        await asyncio.sleep(sleep_interval_seconds)


async def initiate_stage(app, stage_config):
    """
    Initiate a load-shedding stage based on the configuration.
    """
    print(f"Initiating Stage: {stage_config.get('description', 'No Description')}")
    for point in stage_config.get("bacnet_points", []):
        await app.do_write(
            point["address"],
            point["bacnet_obj_id"],
            point["write_value"],
            point["write_priority"],
        )


async def release_stage(app, stage_config):
    """
    Release a load-shedding stage based on the configuration.
    """
    print(f"Releasing Stage: {stage_config.get('description', 'No Description')}")
    for point in stage_config.get("bacnet_points", []):
        await app.do_write(
            point["address"],
            point["bacnet_obj_id"],
            point["release_value"],
            point["write_priority"],
        )
