"""Constants for Skoda Elroq Smart Charging integration."""

DOMAIN = "skoda_elroq_smart_charging"

# Config entry keys
CONF_MQTT_TOPIC_BASE = "mqtt_topic_base"
CONF_CONTRACT_POWER_W = "contract_power_w"
CONF_BATTERY_CAPACITY_KWH = "battery_capacity_kwh"
CONF_VEHICLE_SOC_ENTITY = "vehicle_soc_entity"
CONF_VEHICLE_CHARGE_LIMIT_ENTITY = "vehicle_charge_limit_entity"
CONF_VEHICLE_CONNECTED_ENTITY = "vehicle_connected_entity"
CONF_GRID_POWER_ENTITY = "grid_power_entity"
CONF_PV_POWER_ENTITY = "pv_power_entity"
CONF_WALLBOX_POWER_ENTITY = "wallbox_power_entity"
CONF_WALLBOX_VOLTAGE_ENTITY = "wallbox_voltage_entity"
CONF_TARIFF_BAND_ENTITY = "tariff_band_entity"
CONF_WALLBOX_STATE_ENTITY = "wallbox_state_entity"

# Defaults
DEFAULT_MQTT_TOPIC_BASE = "prism/1"
DEFAULT_CONTRACT_POWER_W = 5700
DEFAULT_BATTERY_CAPACITY_KWH = 59.0
DEFAULT_ALLOWED_IMPORT_W = 200
DEFAULT_MIN_CHARGE_CURRENT_A = 6
DEFAULT_MAX_CHARGE_CURRENT_A = 16
DEFAULT_NIGHT_POWER_LIMIT_W = 3000
DEFAULT_USER_SOC_TARGET = 50
DEFAULT_VEHICLE_SOC_TARGET = 80
DEFAULT_SAFETY_MARGIN_W = 300

# Charging modes
CHARGING_MODE_IDLE = "idle"
CHARGING_MODE_PV_SURPLUS = "fv_surplus"
CHARGING_MODE_NIGHT_F3 = "notturna_f3"
CHARGING_MODE_FORCE = "forza"
CHARGING_MODE_MASTER_STOP = "master_stop"

CHARGING_MODES = [
    CHARGING_MODE_IDLE,
    CHARGING_MODE_PV_SURPLUS,
    CHARGING_MODE_NIGHT_F3,
    CHARGING_MODE_FORCE,
    CHARGING_MODE_MASTER_STOP,
]

# MQTT wallbox modes
MQTT_MODE_SOLAR = 1
MQTT_MODE_NORMAL = 2
MQTT_MODE_PAUSE = 3

# Tariff bands (Italian F1/F2/F3)
TARIFF_F1 = "F1"
TARIFF_F2 = "F2"
TARIFF_F3 = "F3"

# Attribute keys
ATTR_CHARGING_MODE = "charging_mode"
ATTR_CURRENT_SOC = "current_soc"
ATTR_TARGET_SOC = "target_soc"
ATTR_PV_SURPLUS = "pv_surplus_w"
ATTR_GRID_POWER = "grid_power_w"
ATTR_WALLBOX_CURRENT = "wallbox_current_a"
ATTR_LAST_AUTH = "last_authorization"
ATTR_LAST_REVOKE = "last_revoke"
ATTR_TARIFF_BAND = "tariff_band"

# Sensor unique ID suffixes
SENSOR_CHARGING_MODE = "charging_mode"
SENSOR_PV_SURPLUS = "pv_surplus"
SENSOR_TARGET_SOC = "target_soc"
SENSOR_TIME_REMAINING = "time_remaining"
SENSOR_CHARGE_END_TIME = "charge_end_time"
SENSOR_WALLBOX_CURRENT_TARGET = "wallbox_current_target"

# Switch unique ID suffixes
SWITCH_MASTER_STOP = "master_stop"
SWITCH_FORCE_CHARGE = "force_charge"
SWITCH_SOLAR_CONTROLLER = "solar_controller"

# Number unique ID suffixes
NUMBER_USER_SOC_TARGET = "user_soc_target"
NUMBER_VEHICLE_SOC_TARGET = "vehicle_soc_target"
NUMBER_CONTRACT_POWER = "contract_power"
NUMBER_ALLOWED_IMPORT = "allowed_import"
NUMBER_NIGHT_POWER_LIMIT = "night_power_limit"
