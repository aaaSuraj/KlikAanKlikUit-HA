"""Constants for KlikAanKlikUit ICS-2000 integration."""

DOMAIN = "kaku_ics2000"

# API Endpoints
AUTH_ENDPOINT = "https://ics2000.trustsmartcloud.com/gateway.php"
SYNC_ENDPOINT = "https://trustsmartcloud2.com/ics2000_api/gateway.php"

# Configuration
CONF_AES_KEY = "aes_key"
CONF_ENTITY_BLACKLIST = "entity_blacklist"
CONF_TRIES = "tries"
CONF_SLEEP = "sleep"

DEFAULT_PORT = 2012
DEFAULT_TRIES = 3
DEFAULT_SLEEP = 0.1

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

# Events
EVENT_DEVICE_DISCOVERED = f"{DOMAIN}_device_discovered"
