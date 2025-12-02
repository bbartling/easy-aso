# VAV-specific Definition class
class VavDefinition:
    def __init__(
        self, address, damper_position_obj_id, airflow_obj_id, airflow_setpoint_obj_id
    ):
        self.address = address
        self.damper_position_obj_id = damper_position_obj_id
        self.airflow_obj_id = airflow_obj_id
        self.airflow_setpoint_obj_id = airflow_setpoint_obj_id


# AHU-specific Definition class with tuning constants
class AhuDefinition:
    def __init__(
        self,
        ip,
        fan_speed_obj_id,
        static_pressure_obj_id,
        vav_configs,
        SP0,
        SPmin,
        SPmax,
        SPtrim,
        SPres,
        SPres_max,
        I,
        FAN_MIN_SPEED,
    ):
        self.ip = ip
        self.fan_speed_obj_id = fan_speed_obj_id
        self.static_pressure_obj_id = static_pressure_obj_id
        self.vav_configs = vav_configs
        self.SP0 = SP0
        self.SPmin = SPmin
        self.SPmax = SPmax
        self.SPtrim = SPtrim
        self.SPres = SPres
        self.SPres_max = SPres_max
        self.I = I
        self.FAN_MIN_SPEED = FAN_MIN_SPEED
        self.current_sp = SP0
        self.total_pressure_increase = 0
