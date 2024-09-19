# easy_aso/algorithms/load_shed/load_shed_algorithm.py

import asyncio


async def load_shed(app, config_dict, max_iterations=None):
    last_operation_time = 0
    current_stage = 0
    iterations = 0
    stages = config_dict.get("stages", [])
    sleep_interval_seconds = config_dict.get("SLEEP_INTERVAL_SECONDS", 60)
    stage_up_down_timer = config_dict.get("STAGE_UP_DOWN_TIMER", 300)
    power_threshold = config_dict.get("POWER_THRESHOLD", 120.0)
    power_meter_bacnet_addr = config_dict.get("POWER_MTR_BACNET_ADDR")
    power_meter_bacnet_obj_id = config_dict.get("POWER_MTR_BACNET_OBJ_ID")

    while True:
        # Optional limit for testing (break after certain iterations)
        if max_iterations is not None and iterations >= max_iterations:
            break

        # Await the async mock call to get the optimization enabled status
        opt_status = await app.get_optimization_enabled_status()
        print(f"Opt Enabled BV Status bool: {opt_status}")

        # Read the building power
        building_power = await app.do_read(
            power_meter_bacnet_addr, power_meter_bacnet_obj_id
        )
        print("Building power is", building_power)

        current_time = asyncio.get_event_loop().time()
        time_elapsed = current_time - last_operation_time

        # Calculate remaining time for stage up/down
        if time_elapsed < stage_up_down_timer:
            stage_timer_remaining = int(stage_up_down_timer - time_elapsed)
        else:
            stage_timer_remaining = 0  # Set to 0 to indicate no time left

        # Staging logic
        if building_power > power_threshold:
            # Move to next stage if timer has expired
            if time_elapsed >= stage_up_down_timer:
                if current_stage < len(stages):
                    current_stage += 1
                    last_operation_time = current_time
                    print(f"Initiating Stage {current_stage}")
                    await initiate_stage(app, stages[current_stage - 1])
                else:
                    print(f"Stage {current_stage} is already at maximum level.")
            print(
                f"Waiting for stage up/down timer.\n"
                f"Time remaining: {stage_timer_remaining} seconds."
            )
        elif building_power <= power_threshold:
            # Release stages if power is below the threshold
            if current_stage > 0 and time_elapsed >= stage_up_down_timer:
                await release_stage(app, stages[current_stage - 1])
                current_stage -= 1
                last_operation_time = current_time
                print(f"Releasing Stage {current_stage + 1}")
            elif current_stage == 0:
                print("All stages released. Building power is below threshold.")

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
