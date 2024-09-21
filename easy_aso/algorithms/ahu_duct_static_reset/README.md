
## AHU Duct Static Pressure Reset Algorithm Description

The AHU Duct Static Pressure Reset algorithm in EasyASO dynamically adjusts the static pressure setpoint of an AHU (Air Handling Unit) to optimize VAV (Variable Air Volume) box performance while maintaining energy efficiency. The algorithm monitors damper positions and airflow setpoints across multiple VAV boxes, and it adjusts the AHU static pressure based on system demand.

The algorithm supports ignoring the highest damper positions (which may indicate "rogue zones") to avoid overcompensating static pressure for individual VAV boxes that are persistently underperforming. The static pressure is trimmed or increased based on VAV requests, with constraints to prevent excessive pressure increases or decreases.

## Configuration Dictionary (`config_dict`) Setup in `main.py`

The `config_dict` allows you to customize the static pressure reset behavior, including the number of VAV boxes, BACnet addresses, and pressure limits. This setup ensures that you can define the system's limits and conditions under which static pressure is adjusted.

### General Settings:

- **`VAV_BOXES`**: A list of dictionaries representing each VAV box in the system. Each VAV box contains the following keys:
  - **`address`**: The BACnet address of the VAV box (e.g., `"10.200.200.101"`).
  - **`damper_obj_id`**: The object identifier for the VAV box's damper position (e.g., `"analog-input,1"`).
  - **`airflow_setpoint_obj_id`**: The object identifier for the VAV box's airflow setpoint (e.g., `"analog-input,2"`).

- **`SP0`**: The initial static pressure setpoint for the AHU (e.g., `0.5` inches WC).
- **`SPmin`**: The minimum allowable static pressure setpoint (e.g., `0.1` inches WC).
- **`SPmax`**: The maximum allowable static pressure setpoint (e.g., `2.0` inches WC).
- **`Td`**: The initial startup delay (in minutes) before the algorithm starts adjusting the static pressure (e.g., `0.1` or 6 seconds).
- **`T`**: The interval (in minutes) between static pressure adjustments (e.g., `0.02` or 2 seconds).
- **`I`**: The number of highest damper positions to ignore when calculating pressure adjustments (e.g., `1` to ignore the highest damper).
- **`SPtrim`**: The amount to decrease static pressure when no reset requests are made (e.g., `-0.05` inches WC).
- **`SPres`**: The amount to increase static pressure for each reset request (e.g., `0.06` inches WC).
- **`SPres_max`**: The maximum cumulative pressure increase allowed from the initial setpoint (e.g., `0.13` inches WC).

- **`AHU_STATIC_PRESSURE_BACNET_ADDR`**: The BACnet address of the AHU static pressure setpoint (e.g., `"10.200.200.233"`).
- **`AHU_STATIC_PRESSURE_OBJ_ID`**: The object identifier for the AHU's static pressure setpoint (e.g., `"analog-output,1"`).
- **`AHU_STATIC_PRESSURE_PRIORITY`**: The priority for BACnet writes when adjusting the static pressure (e.g., `8`).

### Static Pressure Adjustment Logic:

1. The algorithm reads the damper position and airflow setpoint for each VAV box.
2. It calculates the number of reset requests based on airflow and damper conditions:
   - If the damper position is >95% and airflow is <50% of the setpoint, it sends 3 reset requests.
   - If the damper position is >95% and airflow is <70% of the setpoint, it sends 2 reset requests.
   - If the damper position is >95%, it sends 1 reset request.
   - If the damper position is <95%, no reset requests are sent.
3. The algorithm ignores the highest `I` damper positions (if specified) to avoid overcompensating for rogue zones.
4. The static pressure is increased or decreased based on the number of reset requests, ensuring it stays within the specified limits (`SPmin` to `SPmax`).
5. The system runs on a periodic cycle (`T` minutes), adjusting the pressure incrementally.

### Example `config_dict`:

```python
config_dict = {
    "VAV_BOXES": [
        {"address": "10.200.200.101", "damper_obj_id": "analog-input,1", "airflow_setpoint_obj_id": "analog-input,2"},
        {"address": "10.200.200.102", "damper_obj_id": "analog-input,1", "airflow_setpoint_obj_id": "analog-input,2"},
    ],
    "SP0": 0.5,
    "SPmin": 0.1,
    "SPmax": 2.0,
    "Td": 0.1,  # Startup delay (6 seconds)
    "T": 0.02,  # Adjustment period (2 seconds)
    "I": 1,  # Ignore the highest damper position
    "SPtrim": -0.05,  # Trim amount
    "SPres": 0.06,  # Response amount
    "SPres_max": 0.13,  # Maximum pressure increase
    "AHU_STATIC_PRESSURE_BACNET_ADDR": "10.200.200.233",
    "AHU_STATIC_PRESSURE_OBJ_ID": "analog-output,1",
    "AHU_STATIC_PRESSURE_PRIORITY": 8  # BACnet write priority
}
```

This configuration ensures efficient management of static pressure in AHUs, helping maintain optimal airflow conditions in VAV systems while preventing excessive energy usage.
