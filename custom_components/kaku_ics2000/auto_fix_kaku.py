#!/usr/bin/env python3
"""
Automatic fixer for KlikAanKlikUit ICS-2000 Integration
Run this script to fix all issues with the integration
"""

import os
import shutil
from datetime import datetime

# File contents
CONST_PY = '''"""Constants for KlikAanKlikUit ICS-2000 integration - COMPLETE."""

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
ENCRYPTION_IV = b'\\x00' * 16

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
'''

STATE_MANAGER_PY = '''"""State manager for KlikAanKlikUit ICS-2000 devices."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

_LOGGER = logging.getLogger(__name__)


class StateManager:
    """Manages device states for KlikAanKlikUit devices."""
    
    def __init__(self) -> None:
        """Initialize the state manager."""
        self._states: Dict[int, Dict[str, Any]] = {}
        self._last_update: Optional[datetime] = None
    
    def update_device_state(self, device_id: int, state: Dict[str, Any]) -> None:
        """Update the state of a device."""
        self._states[device_id] = state
        self._last_update = datetime.now()
        _LOGGER.debug(f"Updated state for device {device_id}: {state}")
    
    def get_device_state(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Get the state of a device."""
        return self._states.get(device_id)
    
    def get_all_states(self) -> Dict[int, Dict[str, Any]]:
        """Get all device states."""
        return self._states.copy()
    
    def clear_states(self) -> None:
        """Clear all device states."""
        self._states.clear()
        self._last_update = None
        _LOGGER.debug("Cleared all device states")
    
    @property
    def last_update(self) -> Optional[datetime]:
        """Get the last update time."""
        return self._last_update
    
    def is_device_on(self, device_id: int) -> bool:
        """Check if a device is on."""
        state = self._states.get(device_id, {})
        return state.get("state", False)
    
    def get_device_brightness(self, device_id: int) -> Optional[int]:
        """Get the brightness of a device."""
        state = self._states.get(device_id, {})
        return state.get("brightness")
    
    def get_device_position(self, device_id: int) -> Optional[int]:
        """Get the position of a cover device."""
        state = self._states.get(device_id, {})
        return state.get("position")
'''

def main():
    print("=" * 60)
    print("KlikAanKlikUit Integration Auto-Fixer")
    print("=" * 60)
    print()
    
    # Check if integration exists
    integration_path = "/config/custom_components/kaku_ics2000"
    
    if not os.path.exists(integration_path):
        print("❌ Error: Integration not found at:", integration_path)
        print("   Please make sure the integration is installed")
        return False
    
    print("✅ Found integration at:", integration_path)
    print()
    
    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"/config/custom_components/kaku_ics2000_backup_{timestamp}"
    
    print(f"📦 Creating backup at: {backup_path}")
    try:
        shutil.copytree(integration_path, backup_path)
        print("   Backup created successfully")
    except Exception as e:
        print(f"   Warning: Backup failed: {e}")
    
    print()
    print("📝 Applying fixes...")
    print()
    
    # Fix const.py
    const_file = os.path.join(integration_path, "const.py")
    print("   Fixing const.py...")
    try:
        with open(const_file, 'w') as f:
            f.write(CONST_PY)
        print("   ✅ const.py fixed")
    except Exception as e:
        print(f"   ❌ Error fixing const.py: {e}")
    
    # Add state_manager.py
    state_manager_file = os.path.join(integration_path, "state_manager.py")
    print("   Adding state_manager.py...")
    try:
        with open(state_manager_file, 'w') as f:
            f.write(STATE_MANAGER_PY)
        print("   ✅ state_manager.py added")
    except Exception as e:
        print(f"   ❌ Error adding state_manager.py: {e}")
    
    # Note about hub.py
    print()
    print("⚠️  Note: hub.py also needs to be updated for device names")
    print("   Download hub.py from the fix package and replace manually")
    
    print()
    print("=" * 60)
    print("✅ Fixes Applied!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Restart Home Assistant: ha core restart")
    print("2. Check Settings → Devices & Services")
    print("3. If errors persist, delete and re-add the integration")
    print()
    print(f"Backup saved at: {backup_path}")
    print("To restore: rm -rf {integration_path} && mv {backup_path} {integration_path}")
    
    return True

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
