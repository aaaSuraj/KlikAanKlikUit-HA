"""Constants for KlikAanKlikUit ICS-2000 integration - COMPLETE."""

# Domain
DOMAIN = "kaku_ics2000"

# API Endpoints
AUTH_ENDPOINT = "https://ics2000.trustsmartcloud.com/gateway.php"
SYNC_ENDPOINT = "https://trustsmartcloud2.com/ics2000_api/gateway.php"

# Configuration constants
CONF_AES_KEY = "aes_key"
CONF_ENTITY_BLACKLIST = "entity_blacklist"
CONF_TRIES = "tries"
CONF_SLEEP = "sleep"
CONF_DEVICE_DISCOVERY = "device_discovery"
CONF_DEVICE_CONFIG_OVERRIDES = "device_config_overrides"
CONF_LOCAL_BACKUP_ADDRESS = "local_backup_address"
CONF_HIDE_RELOAD_SWITCH = "hide_reload_switch"
CONF_SHOW_SCENES = "show_scenes"
CONF_DISCOVER_MESSAGE = "discover_message"

# Default values
DEFAULT_PORT = 2012
DEFAULT_TRIES = 3
DEFAULT_SLEEP = 0.1
DEFAULT_DEVICE_DISCOVERY = True
DEFAULT_HIDE_RELOAD_SWITCH = False
DEFAULT_SHOW_SCENES = False

# Device Types
DEVICE_TYPE_SWITCH = 1
DEVICE_TYPE_DIMMER = 2
DEVICE_TYPE_LIGHT = 3
DEVICE_TYPE_COVER = 4
DEVICE_TYPE_SENSOR = 5

# Attributes
ATTR_DEVICE_ID = "device_id"
ATTR_DEVICE_TYPE = "device_type"
ATTR_DEVICE_MODEL = "device_model"
ATTR_DIMMABLE = "dimmable"
ATTR_ZIGBEE = "zigbee"
ATTR_LAST_COMMAND = "last_command"
ATTR_LAST_UPDATE = "last_update"
ATTR_CONFIDENCE = "confidence"
ATTR_BRIGHTNESS = "brightness"
ATTR_POSITION = "position"
ATTR_STATE = "state"

# Events
EVENT_DEVICE_DISCOVERED = f"{DOMAIN}_device_discovered"
EVENT_DEVICE_UPDATED = f"{DOMAIN}_device_updated"
EVENT_HUB_CONNECTED = f"{DOMAIN}_hub_connected"
EVENT_HUB_DISCONNECTED = f"{DOMAIN}_hub_disconnected"

# Service names
SERVICE_RELOAD = "reload"
SERVICE_IDENTIFY = "identify"
SERVICE_SET_BRIGHTNESS = "set_brightness"
SERVICE_SET_POSITION = "set_position"

# Hub states
HUB_STATE_CONNECTED = "connected"
HUB_STATE_DISCONNECTED = "disconnected"
HUB_STATE_AUTHENTICATING = "authenticating"
HUB_STATE_DISCOVERING = "discovering"

# Command types
COMMAND_ON = 1
COMMAND_OFF = 0
COMMAND_DIM = 2
COMMAND_STOP = 3
COMMAND_OPEN = 4
COMMAND_CLOSE = 5
COMMAND_IDENTIFY = 99

# Update intervals (in seconds)
UPDATE_INTERVAL = 30
DISCOVERY_INTERVAL = 300

# Encryption
ENCRYPTION_HEADER = b'kaku'
ENCRYPTION_IV = b'\x00' * 16

# Device capabilities
CAPABILITY_ON_OFF = "on_off"
CAPABILITY_DIMMABLE = "dimmable"
CAPABILITY_POSITION = "position"
CAPABILITY_COLOR = "color"
CAPABILITY_TEMPERATURE = "temperature"

# Manufacturer info
MANUFACTURER = "KlikAanKlikUit"
MODEL_ICS2000 = "ICS-2000"
SW_VERSION = "1.0.0"
