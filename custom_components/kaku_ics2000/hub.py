"""Hub for KlikAanKlikUit ICS-2000 - FIXED device name extraction."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import random
import socket
import struct
import time
from typing import Any, Callable, Dict, List, Optional

import aiohttp
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from homeassistant.core import HomeAssistant

from .const import (
    ATTR_CONFIDENCE,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_MODEL,
    ATTR_DEVICE_TYPE,
    ATTR_DIMMABLE,
    ATTR_LAST_COMMAND,
    ATTR_LAST_UPDATE,
    ATTR_ZIGBEE,
    AUTH_ENDPOINT,
    DEFAULT_PORT,
    DEFAULT_SLEEP,
    DEFAULT_TRIES,
    DEVICE_TYPE_COVER,
    DEVICE_TYPE_DIMMER,
    DEVICE_TYPE_LIGHT,
    DEVICE_TYPE_SENSOR,
    DEVICE_TYPE_SWITCH,
    DOMAIN,
    EVENT_DEVICE_DISCOVERED,
    SYNC_ENDPOINT,
)
from .state_manager import StateManager

_LOGGER = logging.getLogger(__name__)

# Based on the ics-2000 npm package behavior
HOMEBRIDGE_HEADER = b'kaku'  # Different header than \xAA\xAA


class ICS2000Hub:
    """ICS-2000 Hub with Homebridge-compatible encryption and proper name extraction."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        mac: str,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        aes_key: Optional[str] = None,
        tries: int = DEFAULT_TRIES,
        sleep: int = DEFAULT_SLEEP,
        state_manager: Optional[StateManager] = None,
    ) -> None:
        """Initialize the hub."""
        self.hass = hass
        self.mac = mac.upper().replace(":", "")
        self.mac_formatted = ":".join([self.mac[i:i+2] for i in range(0, 12, 2)])
        self.email = email
        self.password = password
        self.ip_address = ip_address
        self.tries = tries
        self.sleep = sleep
        self.state_manager = state_manager
        
        # Authentication
        self._session = None
        self._home_id = None
        self._gateway_mac = None
        self._aes_key = None
        
        # Devices (each module IS a device)
        self.devices: Dict[int, Dict[str, Any]] = {}
        self.scenes: Dict[int, Dict[str, Any]] = {}
        self.firmware_version = "1.0.0"
        self._connected = False
        self._state_callbacks: List[Callable] = []
        
        # Store raw module data for state updates
        self._raw_modules: Dict[int, Dict[str, Any]] = {}
        
        # Device blacklist
        self.entity_blacklist: List[int] = []
        
        # Command sequence number (Homebridge uses this)
        self._sequence = random.randint(1000, 9999)
    
    def _decrypt_kaku_data(self, encrypted_b64: str) -> Optional[Dict]:
        """Decrypt KlikAanKlikUit data with proper JSON extraction."""
        if not self._aes_key or not encrypted_b64:
            return None
        
        try:
            aes_key = bytes.fromhex(self._aes_key)
            encrypted = base64.b64decode(encrypted_b64)
            
            # Use CBC mode with zero IV (as per KlikAanKlikUit implementation)
            iv = b'\x00' * 16
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(encrypted) + decryptor.finalize()
            
            # Find JSON start (look for { or [)
            json_start = -1
            for i in range(len(decrypted)):
                if decrypted[i:i+1] in [b'{', b'[']:
                    json_start = i
                    break
            
            if json_start == -1:
                return None
            
            # Extract JSON portion
            json_bytes = decrypted[json_start:]
            
            # Remove PKCS7 padding if present
            if len(json_bytes) > 0:
                pad_len = json_bytes[-1]
                if isinstance(pad_len, int) and 0 < pad_len <= 16:
                    # Check if it's valid PKCS7 padding
                    if all(b == pad_len for b in json_bytes[-pad_len:]):
                        json_bytes = json_bytes[:-pad_len]
            
            # Decode to string
            json_str = json_bytes.decode('utf-8', errors='ignore')
            
            # Find the end of JSON (balance brackets)
            depth = 0
            end_pos = 0
            for i, char in enumerate(json_str):
                if char == '{' or char == '[':
                    depth += 1
                elif char == '}' or char == ']':
                    depth -= 1
                    if depth == 0:
                        end_pos = i + 1
                        break
            
            if end_pos > 0:
                json_str = json_str[:end_pos]
                return json.loads(json_str)
            
        except Exception as e:
            _LOGGER.debug(f"Decryption error: {e}")
        
        return None
    
    def _extract_device_name(self, module_data: Dict) -> Optional[str]:
        """Extract device name from module data."""
        try:
            # Try to decrypt the 'data' field which contains the actual device names
            if 'data' in module_data and module_data['data']:
                decrypted = self._decrypt_kaku_data(module_data['data'])
                
                if decrypted and 'module' in decrypted:
                    module = decrypted['module']
                    
                    # First try to get the module name directly
                    if 'name' in module and module['name']:
                        return module['name']
                    
                    # If module has entities, get the first entity's name
                    if 'entities' in module and module['entities']:
                        for entity in module['entities']:
                            if 'name' in entity and entity['name']:
                                return entity['name']
                    
                    # Try device field
                    if 'device' in module and module['device']:
                        return module['device']
            
            # Fallback: try to decrypt status field
            if 'status' in module_data and module_data['status']:
                decrypted = self._decrypt_kaku_data(module_data['status'])
                
                if decrypted and 'module' in decrypted:
                    module = decrypted['module']
                    
                    if 'name' in module and module['name']:
                        return module['name']
                    
                    if 'device' in module and module['device']:
                        return module['device']
            
        except Exception as e:
            _LOGGER.debug(f"Error extracting device name: {e}")
        
        return None
    
    def _guess_device_type(self, device_name: str, device_value: int = 0) -> int:
        """Guess device type from name and value."""
        name_lower = device_name.lower()
        
        # Check for specific device types
        if any(x in name_lower for x in ["motion", "sensor", "detector", "pir"]):
            return DEVICE_TYPE_SENSOR
        elif any(x in name_lower for x in ["dimmer", "dim", "brightness"]):
            return DEVICE_TYPE_DIMMER
        elif any(x in name_lower for x in ["lamp", "light", "bulb", "led"]):
            return DEVICE_TYPE_LIGHT
        elif any(x in name_lower for x in ["blind", "shutter", "curtain", "cover", "screen"]):
            return DEVICE_TYPE_COVER
        elif any(x in name_lower for x in ["plug", "socket", "outlet", "switch"]):
            return DEVICE_TYPE_SWITCH
        
        # Fallback based on device value
        if device_value in [1, 3, 5]:  # Common switch values
            return DEVICE_TYPE_SWITCH
        elif device_value in [2, 4]:  # Common dimmer values
            return DEVICE_TYPE_DIMMER
        
        return DEVICE_TYPE_SWITCH  # Default
    
    def _guess_if_dimmable(self, device_name: str, device_type: int) -> bool:
        """Guess if device is dimmable."""
        if device_type in [DEVICE_TYPE_DIMMER, DEVICE_TYPE_COVER]:
            return True
        
        name_lower = device_name.lower()
        if any(x in name_lower for x in ["dimmer", "dim", "brightness", "dimmable"]):
            return True
        
        return False
    
    async def async_discover_devices(self) -> Dict[int, Dict[str, Any]]:
        """Discover devices with proper name extraction."""
        if not self._aes_key:
            _LOGGER.error("No AES key available")
            return self.devices
        
        _LOGGER.info("Fetching devices with proper names...")
        
        sync_data = {
            'email': self.email,
            'mac': self._gateway_mac or self.mac,
            'action': 'sync',
            'password_hash': self.password,
            'home_id': self._home_id or '',
        }
        
        try:
            async with self._session.post(
                SYNC_ENDPOINT,
                data=sync_data,
                timeout=aiohttp.ClientTimeout(total=10),
                ssl=False,
            ) as response:
                if response.status == 200:
                    text = await response.text()
                    sync_response = json.loads(text)
                    
                    if isinstance(sync_response, list):
                        _LOGGER.info(f"Got {len(sync_response)} modules/devices")
                        
                        device_count = 0
                        
                        for module_idx, module_data in enumerate(sync_response):
                            module_id = int(module_data.get('id', 0))
                            
                            if module_id <= 0 or module_id in self.entity_blacklist:
                                continue
                            
                            # Store raw module data
                            self._raw_modules[module_id] = module_data
                            
                            # Extract the actual device name
                            device_name = self._extract_device_name(module_data)
                            
                            # If no name found, use a fallback
                            if not device_name:
                                device_name = f"Device {module_id}"
                                _LOGGER.debug(f"No name found for module {module_id}, using fallback")
                            else:
                                _LOGGER.info(f"✓ Found device name: '{device_name}' for module {module_id}")
                            
                            # Determine device type
                            device_value = module_data.get('device', 0)
                            if isinstance(device_value, str) and device_value.isdigit():
                                device_value = int(device_value)
                            
                            device_type = self._guess_device_type(device_name, device_value)
                            is_dimmable = self._guess_if_dimmable(device_name, device_type)
                            
                            # Get current state
                            current_state = False
                            version_status = module_data.get('version_status', '0')
                            if version_status and version_status != '0':
                                try:
                                    # Odd version numbers often mean "on" state
                                    current_state = (int(version_status) % 2) == 1
                                except:
                                    pass
                            
                            # Create device with proper name and state
                            self.devices[module_id] = {
                                ATTR_DEVICE_ID: module_id,
                                ATTR_DEVICE_TYPE: device_type,
                                ATTR_DEVICE_MODEL: device_name,  # Use the extracted name here!
                                ATTR_DIMMABLE: is_dimmable,
                                ATTR_ZIGBEE: False,
                                "state": current_state,
                                "brightness": 50 if is_dimmable else None,
                                "position": None,
                                "device_value": device_value,
                                "version_status": version_status,
                                "version_data": module_data.get('version_data'),
                            }
                            
                            device_count += 1
                            _LOGGER.info(f"✓ Created device {device_count}: '{device_name}' (Type: {device_type}, Dimmable: {is_dimmable})")
                        
                        _LOGGER.info(f"✓ Successfully created {device_count} devices with proper names!")
                        
                        # Fire discovery event
                        self.hass.bus.async_fire(
                            EVENT_DEVICE_DISCOVERED,
                            {
                                "hub": self.mac,
                                "device_count": device_count,
                            },
                        )
                    else:
                        _LOGGER.error(f"Unexpected response format")
                        
        except Exception as e:
            _LOGGER.error(f"Device discovery error: {e}")
        
        return self.devices
    
    # ... rest of the hub.py implementation remains the same ...
    
    async def async_turn_on(self, device_id: int) -> None:
        """Turn on a device."""
        await self._send_command(device_id, 1)
    
    async def async_turn_off(self, device_id: int) -> None:
        """Turn off a device."""
        await self._send_command(device_id, 0)
    
    async def async_authenticate(self) -> bool:
        """Authenticate with the cloud service."""
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        auth_data = {
            'email': self.email,
            'mac': self.mac,
            'password_hash': self.password,
            'action': 'check',
        }
        
        try:
            async with self._session.post(
                AUTH_ENDPOINT,
                data=auth_data,
                timeout=aiohttp.ClientTimeout(total=10),
                ssl=False,
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    if result.get('status') == 'ok':
                        self._home_id = result.get('home_id', '')
                        self._gateway_mac = result.get('mac', self.mac)
                        self._aes_key = result.get('aes_key', '')
                        
                        _LOGGER.info(f"✓ Authenticated successfully! AES key: {self._aes_key[:8]}...")
                        self._connected = True
                        return True
                    else:
                        _LOGGER.error(f"Authentication failed: {result}")
        
        except Exception as e:
            _LOGGER.error(f"Authentication error: {e}")
        
        self._connected = False
        return False
    
    async def async_close(self) -> None:
        """Close the hub connection."""
        if self._session:
            await self._session.close()
            self._session = None
        self._connected = False
    
    def get_device(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Get device by ID."""
        return self.devices.get(device_id)
    
    def get_all_devices(self) -> List[Dict[str, Any]]:
        """Get all devices."""
        return list(self.devices.values())
    
    @property
    def connected(self) -> bool:
        """Return connection status."""
        return self._connected
