## Load Shed Algorithm Description

The load-shedding algorithm in EasyASO monitors building power consumption and dynamically adjusts building systems in multiple stages to reduce power usage when it exceeds a predefined threshold. The algorithm is highly customizable and can handle any number of load-shedding stages, allowing users to define their own strategies through a configuration dictionary (`config_dict`).

The algorithm operates through stages, where each stage defines specific actions to take when power consumption exceeds the threshold. The algorithm uses timers to control when to initiate or release each stage. If the power remains above the threshold for a specified period (`STAGE_UP_DOWN_TIMER`), the next stage is activated. Conversely, if the power drops below the threshold, the algorithm reverses the stages to return the system to normal operation.

## Configuration Dictionary (`config_dict`) Setup in `main.py`

The `config_dict` allows you to customize the load-shedding behavior, including the number of stages, BACnet point addresses, write values, and thresholds. This flexible setup lets you define as many stages as needed, with specific actions for each stage.

### General Settings:

- **`POWER_MTR_BACNET_ADDR`**: The BACnet address of the power meter that monitors building power consumption (e.g., `"10.200.200.233"`).
- **`POWER_MTR_BACNET_OBJ_ID`**: The object identifier for the power meter's value (e.g., `"analog-input,7"`).
- **`POWER_THRESHOLD`**: The power consumption threshold (in kW) that triggers load shedding (e.g., `120.0`).
- **`SLEEP_INTERVAL_SECONDS`**: The interval (in seconds) between each monitoring cycle (e.g., `60`).
- **`DUTY_CYCLE_INTERVAL_SECONDS`**: The minimum time (in seconds) each load-shedding stage should run before any changes (e.g., `900` or 15 minutes).
- **`STAGE_UP_DOWN_TIMER`**: The time (in seconds) to wait before moving up to the next stage or releasing a stage (e.g., `300` or 5 minutes).

### Stages:

- **`stages`**: A list of dictionaries defining each load-shedding stage. You can define any number of stages here, each with its own BACnet points and actions:
  - **`description`**: A brief description of the stage (e.g., `"Stage 1: Reset zone setpoints upward."`).
  - **`bacnet_points`**: A list of BACnet points to control in this stage. Each point is a dictionary with the following keys:
    - **`address`**: The BACnet address of the device (e.g., `"10.200.200.233"`).
    - **`bacnet_obj_id`**: The BACnet object identifier (e.g., `"analog-value,2"`).
    - **`write_value`**: The value to write when initiating this stage (e.g., `78.0`).
    - **`release_value`**: The value to write when releasing this stage (e.g., `"null"` to reset).
    - **`write_priority`**: The priority of the BACnet write operation (e.g., `10`).

