DOMAIN = "tuya_tdk_thermostat"

CONF_ACCESS_ID = "access_id"
CONF_ACCESS_SECRET = "access_secret"
CONF_ENDPOINT = "endpoint"
CONF_DEVICE_IDS = "device_ids"

DEFAULT_SCAN_INTERVAL = 10  # seconds
TEMP_SCALE = 0.1  # device uses tenths of °C

# Device DP codes derived from your shadow/status
DP_SWITCH = "switch"
DP_MODE = "mode"                 # presets: e.g., home/away/auto/...
DP_TEMP_SET = "temp_set"         # scaled int
DP_TEMP_CURRENT = "temp_current" # scaled int
DP_UPPER_TEMP = "upper_temp"     # scaled int (max)
DP_LOWER_TEMP = "lower_temp"     # scaled int (min)
DP_WORK_STATE = "work_state"     # "heating" | "stop"

# Extras
DP_CHILD_LOCK = "child_lock"
DP_FROST = "frost"
DP_BATTERY_PCT = "battery_percentage"
DP_WORK_DAYS = "work_days"
DP_QDWENCHA = "qidongwencha"     # hysteresis
DP_DORMANT_SWITCH = "dormant_switch"
DP_DORMANT_TIME_SET = "dormant_time_set"
DP_FACTORY_RESET = "factory_reset"
DP_WEEK_UP_BTN = "week_up_btn"
DP_WEEK_PROGRAM3 = "week_program3"
