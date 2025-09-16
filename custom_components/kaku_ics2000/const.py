"""
Constants for KlikAanKlikUit ICS-2000 integration.
Auto-generated complete constants file with ALL possible constants.
"""

from __future__ import annotations

# Domain
DOMAIN = "kaku_ics2000"

# API Endpoints
AUTH_ENDPOINT = "https://ics2000.trustsmartcloud.com/gateway.php"
SYNC_ENDPOINT = "https://trustsmartcloud2.com/ics2000_api/gateway.php"

# Configuration
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
CONF_MQTT_ENABLE = "mqtt_enable"
CONF_MQTT_BROKER = "mqtt_broker"
CONF_MQTT_PORT = "mqtt_port"
CONF_MQTT_USERNAME = "mqtt_username"
CONF_MQTT_PASSWORD = "mqtt_password"
CONF_MQTT_TOPIC = "mqtt_topic"
CONF_STATE_MANAGER = "state_manager"
CONF_GATEWAY_MAC = "gateway_mac"
CONF_HOME_ID = "home_id"

# Defaults
DEFAULT_PORT = 2012
DEFAULT_TRIES = 3
DEFAULT_SLEEP = 0.1
DEFAULT_DEVICE_DISCOVERY = True
DEFAULT_HIDE_RELOAD_SWITCH = False
DEFAULT_SHOW_SCENES = False
DEFAULT_MQTT_ENABLE = False
DEFAULT_MQTT_PORT = 1883

# Device Types
DEVICE_TYPE_SWITCH = 1
DEVICE_TYPE_DIMMER = 2
DEVICE_TYPE_LIGHT = 3
DEVICE_TYPE_COVER = 4
DEVICE_TYPE_SENSOR = 5
DEVICE_TYPE_SCENE = 6
DEVICE_TYPE_REMOTE = 7
DEVICE_TYPE_THERMOSTAT = 8
DEVICE_TYPE_CAMERA = 9
DEVICE_TYPE_LOCK = 10

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
ATTR_TEMPERATURE = "temperature"
ATTR_HUMIDITY = "humidity"
ATTR_BATTERY = "battery"
ATTR_SIGNAL = "signal"
ATTR_FIRMWARE = "firmware"
ATTR_VERSION = "version"

# Events
EVENT_DEVICE_DISCOVERED = f"{DOMAIN}_device_discovered"
EVENT_DEVICE_UPDATED = f"{DOMAIN}_device_updated"
EVENT_HUB_CONNECTED = f"{DOMAIN}_hub_connected"
EVENT_HUB_DISCONNECTED = f"{DOMAIN}_hub_disconnected"
EVENT_SCENE_ACTIVATED = f"{DOMAIN}_scene_activated"
EVENT_COMMAND_SENT = f"{DOMAIN}_command_sent"
EVENT_COMMAND_FAILED = f"{DOMAIN}_command_failed"

# Services
SERVICE_RELOAD = "reload"
SERVICE_IDENTIFY = "identify"
SERVICE_SET_BRIGHTNESS = "set_brightness"
SERVICE_SET_POSITION = "set_position"
SERVICE_ACTIVATE_SCENE = "activate_scene"
SERVICE_SEND_COMMAND = "send_command"
SERVICE_DISCOVER = "discover"
SERVICE_SYNC = "sync"

# Hub States
HUB_STATE_CONNECTED = "connected"
HUB_STATE_DISCONNECTED = "disconnected"
HUB_STATE_AUTHENTICATING = "authenticating"
HUB_STATE_DISCOVERING = "discovering"
HUB_STATE_ERROR = "error"
HUB_STATE_READY = "ready"

# Commands
COMMAND_ON = 1
COMMAND_OFF = 0
COMMAND_DIM = 2
COMMAND_STOP = 3
COMMAND_OPEN = 4
COMMAND_CLOSE = 5
COMMAND_UP = 6
COMMAND_DOWN = 7
COMMAND_LEFT = 8
COMMAND_RIGHT = 9
COMMAND_IDENTIFY = 99

# Intervals
UPDATE_INTERVAL = 30
DISCOVERY_INTERVAL = 300
PING_INTERVAL = 60
RECONNECT_INTERVAL = 10

# Encryption
ENCRYPTION_HEADER = b'kaku'
ENCRYPTION_IV = b'\x00' * 16
ENCRYPTION_MODE = "CBC"
ENCRYPTION_PADDING = "PKCS7"

# Capabilities
CAPABILITY_ON_OFF = "on_off"
CAPABILITY_DIMMABLE = "dimmable"
CAPABILITY_POSITION = "position"
CAPABILITY_COLOR = "color"
CAPABILITY_TEMPERATURE = "temperature"
CAPABILITY_SCENE = "scene"
CAPABILITY_BATTERY = "battery"

# Device Info
MANUFACTURER = "KlikAanKlikUit"
MODEL_ICS2000 = "ICS-2000"
SW_VERSION = "1.0.0"
HW_VERSION = "1.0"

# Protocol
PROTOCOL_VERSION = "2.0"
PROTOCOL_PORT = 2012
PROTOCOL_TIMEOUT = 5.0

# Limits
MAX_DEVICES = 64
MAX_SCENES = 32
MAX_RETRIES = 3
MAX_NAME_LENGTH = 32

