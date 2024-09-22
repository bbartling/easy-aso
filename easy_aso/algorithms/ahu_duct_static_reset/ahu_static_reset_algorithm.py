import asyncio


class ConfigError(Exception):
    """Custom exception for invalid configuration"""

    pass


class AHUStaticPressureReset:
    def __init__(self, config_dict):
        """Initialize the AHU static pressure reset algorithm with the given config."""
        self.config_dict = config_dict
        self.validate_ahu_config(config_dict)
        self.current_sp = config_dict["SP0"]
        self.total_pressure_increase = 0

    def validate_ahu_config(self, config_dict):
        """Validate AHU config dictionary for required keys and correct data types."""
        required_keys = {
            "VAV_BOXES": list,  # List of BACnet addresses for the VAV boxes
            "SP0": (int, float),  # Initial static pressure setpoint
            "SPmin": (int, float),  # Minimum static pressure
            "SPmax": (int, float),  # Maximum static pressure
            "Td": (int, float),  # Startup delay (minutes)
            "T": (int, float),  # Adjustment period (minutes)
            "I": int,  # Ignore requests count
            "SPtrim": (int, float),  # Trim amount
            "SPres": (int, float),  # Response amount
            "SPres_max": (int, float),  # Maximum response amount
            "AHU_STATIC_PRESSURE_BACNET_ADDR": str,  # BACnet address for AHU pressure setpoint
            "AHU_STATIC_PRESSURE_OBJ_ID": str,  # BACnet object ID for AHU pressure setpoint
            "AHU_STATIC_PRESSURE_PRIORITY": int,  # BACnet priority for writing the static pressure
        }

        for key, expected_type in required_keys.items():
            if key not in config_dict:
                raise ConfigError(f"Missing required config key: {key}")
            if not isinstance(config_dict[key], expected_type):
                raise ConfigError(
                    f"Incorrect type for {key}. Expected {expected_type}, got {type(config_dict[key])}"
                )

    async def run(self, app, max_iterations=None):
        """Run the AHU static pressure reset algorithm."""
        Td = self.config_dict["Td"]
        T = self.config_dict["T"]
        I = self.config_dict["I"]
        SPres_max = self.config_dict["SPres_max"]
        SPres = self.config_dict["SPres"]
        SPtrim = self.config_dict["SPtrim"]
        SPmin = self.config_dict["SPmin"]
        SPmax = self.config_dict["SPmax"]

        iterations = 0

        # Initial startup delay
        await asyncio.sleep(Td * 60)

        while True:
            if max_iterations is not None and iterations >= max_iterations:
                break

            total_reset_requests = 0
            damper_data = []

            # Collect damper positions and airflow setpoints for all VAV boxes
            for vav_box in self.config_dict["VAV_BOXES"]:
                damper_position = await app.do_read(
                    vav_box["address"], vav_box["damper_obj_id"]
                )
                airflow_setpoint = await app.do_read(
                    vav_box["address"], vav_box["airflow_setpoint_obj_id"]
                )
                damper_data.append((damper_position, airflow_setpoint))

            # Sort the damper data by damper position in descending order
            damper_data.sort(reverse=True, key=lambda x: x[0])

            # Ignore the highest I dampers
            damper_data = damper_data[I:]

            # Logic to determine the number of reset requests for the remaining VAV boxes
            for damper_position, airflow_setpoint in damper_data:
                if airflow_setpoint > 0 and damper_position > 95:
                    if airflow_setpoint < 0.5 * airflow_setpoint:
                        total_reset_requests += 3
                    elif airflow_setpoint < 0.7 * airflow_setpoint:
                        total_reset_requests += 2
                    else:
                        total_reset_requests += 1
                elif damper_position < 95:
                    total_reset_requests = 0

            # Adjust the static pressure
            if total_reset_requests > 0:
                # Only increase pressure if we haven't reached the maximum increase (SPres_max)
                if self.total_pressure_increase < SPres_max:
                    pressure_increase = min(
                        SPres, SPres_max - self.total_pressure_increase
                    )  # Ensure we don’t exceed SPres_max
                    self.current_sp = min(
                        self.current_sp + pressure_increase, SPmax
                    )  # Cap at SPmax
                    self.total_pressure_increase += pressure_increase
                else:
                    print(
                        f"Maximum pressure increase ({SPres_max} inches) reached, no further increase."
                    )
            else:
                self.current_sp = max(self.current_sp + SPtrim, SPmin)  # Cap at SPmin

            # Send the updated static pressure setpoint via BACnet
            await self.initiate_pressure_change(app, self.current_sp)

            print(f"Adjusting static pressure to {self.current_sp} inches WC")

            iterations += 1
            await asyncio.sleep(T * 60)  # Wait for next adjustment cycle

    async def initiate_pressure_change(self, app, new_setpoint):
        """
        Helper function to send the pressure change command.
        """
        # Use the BACnet address, object ID, and priority from the config_dict
        address = self.config_dict["AHU_STATIC_PRESSURE_BACNET_ADDR"]
        obj_id = self.config_dict["AHU_STATIC_PRESSURE_OBJ_ID"]
        priority = self.config_dict["AHU_STATIC_PRESSURE_PRIORITY"]

        # Write the new static pressure to the appropriate BACnet point
        await app.do_write(address, obj_id, new_setpoint, priority)
