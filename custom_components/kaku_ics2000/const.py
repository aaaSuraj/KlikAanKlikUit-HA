"""Constants for the KlikAanKlikUit ICS-2000 integration - Homebridge Compatible."""

from typing import Final

# Domain
DOMAIN: Final = "kaku_ics2000"

# Configuration
CONF_AES_KEY: Final = "aes_key"
CONF_TRIES: Final = "tries"
CONF_SLEEP: Final = "sleep"
CONF_STATE_RESTORE: Final = "state_restore"
CONF_DEVICE_DISCOVERY: Final = "device_discovery"
CONF_MQTT_ENABLE: Final = "mqtt_enable"
CONF_MQTT_TOPIC: Final = "mqtt_topic"
CONF_ENTITY_BLACKLIST: Final = "entity_blacklist"  # Homebridge compatible
CONF_SHOW_SCENES: Final = "show_scenes"  # Homebridge feature
CONF_CUSTOM_DISCOVER_MESSAGE: Final = "discover_message"  # Homebridge feature
CONF_START_REST_SERVER: Final = "start_rest_server"  # Homebridge feature
CONF_REST_SERVER_PORT: Final = "rest_server_port"  # Homebridge feature

# Defaults
DEFAULT_TRIES: Final = 3
DEFAULT_SLEEP: Final = 2
DEFAULT_STATE_RESTORE: Final = True
DEFAULT_DEVICE_DISCOVERY: Final = True
DEFAULT_MQTT_ENABLE: Final = False
DEFAULT_MQTT_TOPIC: Final = "kaku_ics2000"
DEFAULT_SHOW_SCENES: Final = True
DEFAULT_REST_SERVER_PORT: Final = 9100

# Device types
DEVICE_TYPE_LIGHT: Final = "light"
DEVICE_TYPE_DIMMER: Final = "dimmer"
DEVICE_TYPE_SWITCH: Final = "switch"
DEVICE_TYPE_COVER: Final = "cover"
DEVICE_TYPE_SENSOR: Final = "sensor"
DEVICE_TYPE_DOORBELL: Final = "doorbell"
DEVICE_TYPE_SCENE: Final = "scene"  # Added for Homebridge compatibility
DEVICE_TYPE_COLOR_TEMP: Final = "color_temperature"  # Added for Homebridge

# Device models (based on product codes)
DEVICE_MODELS = {
    # Lights (433MHz)
    "ACLED": {"type": DEVICE_TYPE_LIGHT, "name": "LED Light", "dimmable": False},
    "AYLED": {"type": DEVICE_TYPE_DIMMER, "name": "Dimmable LED", "dimmable": True},
    "ACD": {"type": DEVICE_TYPE_DIMMER, "name": "Dimmer Module", "dimmable": True},
    
    # Switches (433MHz)
    "ACWS": {"type": DEVICE_TYPE_SWITCH, "name": "Wall Switch", "dimmable": False},
    "ACPN": {"type": DEVICE_TYPE_SWITCH, "name": "Smart Plug", "dimmable": False},
    "AC": {"type": DEVICE_TYPE_SWITCH, "name": "Switch Module", "dimmable": False},
    "AYCT": {"type": DEVICE_TYPE_SWITCH, "name": "Remote Control", "dimmable": False},
    
    # Covers (433MHz)
    "ASUN": {"type": DEVICE_TYPE_COVER, "name": "Roller Blind", "dimmable": False},
    "AMR": {"type": DEVICE_TYPE_COVER, "name": "Motor Controller", "dimmable": False},
    
    # Sensors (433MHz)
    "AMST": {"type": DEVICE_TYPE_SENSOR, "name": "Motion Sensor", "dimmable": False},
    "AWST": {"type": DEVICE_TYPE_SENSOR, "name": "Door/Window Sensor", "dimmable": False},
    "ACDB": {"type": DEVICE_TYPE_DOORBELL, "name": "Doorbell", "dimmable": False},
    
    # Zigbee devices (Z-prefix)
    "ZLED": {"type": DEVICE_TYPE_DIMMER, "name": "Zigbee LED", "dimmable": True, "zigbee": True},
    "ZCC": {"type": DEVICE_TYPE_SWITCH, "name": "Zigbee Plug", "dimmable": False, "zigbee": True},
    "ZSENS": {"type": DEVICE_TYPE_SENSOR, "name": "Zigbee Sensor", "dimmable": False, "zigbee": True},
    
    # Color temperature devices (Homebridge)
    "ZCT": {"type": DEVICE_TYPE_COLOR_TEMP, "name": "Color Temp Light", "dimmable": True, "zigbee": True, "color_temp": True},
}

# Services
SERVICE_IDENTIFY: Final = "identify"
SERVICE_REFRESH_DEVICES: Final = "refresh_devices"
SERVICE_RESET_STATE: Final = "reset_state"
SERVICE_RELOAD: Final = "reload"  # Like Homebridge reload switch
SERVICE_RUN_SCENE: Final = "run_scene"  # Homebridge scene support

# Events
EVENT_DEVICE_DISCOVERED: Final = f"{DOMAIN}_device_discovered"
EVENT_COMMAND_SENT: Final = f"{DOMAIN}_command_sent"
EVENT_STATE_CHANGED: Final = f"{DOMAIN}_state_changed"
EVENT_SCENE_ACTIVATED: Final = f"{DOMAIN}_scene_activated"  # Homebridge feature

# State confidence levels
CONFIDENCE_HIGH: Final = 100  # Just sent command
CONFIDENCE_MEDIUM: Final = 80  # Within 5 minutes
CONFIDENCE_LOW: Final = 60  # Within 1 hour
CONFIDENCE_UNCERTAIN: Final = 40  # Older than 1 hour

# Discovery
DISCOVERY_TIMEOUT: Final = 10  # seconds (like Homebridge)
DISCOVERY_PORT: Final = 2012

# Attributes
ATTR_DEVICE_ID: Final = "device_id"
ATTR_DEVICE_TYPE: Final = "device_type"
ATTR_DEVICE_MODEL: Final = "device_model"
ATTR_LAST_COMMAND: Final = "last_command"
ATTR_LAST_UPDATE: Final = "last_update"
ATTR_CONFIDENCE: Final = "confidence"
ATTR_ZIGBEE: Final = "zigbee"
ATTR_DIMMABLE: Final = "dimmable"
ATTR_BATTERY_LEVEL: Final = "battery_level"
ATTR_RSSI: Final = "rssi"
ATTR_IS_GROUP: Final = "is_group"  # Homebridge group support
ATTR_COLOR_TEMPERATURE: Final = "color_temperature"  # Homebridge feature
ATTR_ENTITY_ID: Final = "entity_id"  # Homebridge entity ID

# Homebridge device type numbers (from TypeScript)
HOMEBRIDGE_DEVICE_TYPES = {
    1: DEVICE_TYPE_SWITCH,
    2: DEVICE_TYPE_DIMMER,
    3: DEVICE_TYPE_LIGHT,
    4: DEVICE_TYPE_COVER,
    5: DEVICE_TYPE_SENSOR,
    6: DEVICE_TYPE_COLOR_TEMP,
}
