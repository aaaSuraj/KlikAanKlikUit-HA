"""Hub for KlikAanKlikUit ICS-2000 with proper device name extraction."""

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

_LOGGER = logging.getLogger(__name__)


class ICS2000Hub:
    """ICS-2000 Hub with proper device name extraction."""
    
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
        state_manager: Optional[Any] = None,
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
        self._aes_key = aes_key
        
        # Devices
        self.devices: Dict[int, Dict[str, Any]] = {}
        self.scenes: Dict[int, Dict[str, Any]] = {}
        self.firmware_version = "1.0.0"
        self._connected = False
        self._state_callbacks: List[Callable] = []
        
        # Store raw module data
        self._raw_modules: Dict[int, Dict[str, Any]] = {}
        
        # Device blacklist
        self.entity_blacklist: List[int] = []
        
        # Command sequence
        self._sequence = random.randint(1000, 9999)
    
    def _decrypt_kaku_data(self, encrypted_b64: str) -> Optional[Dict]:
        """Decrypt KlikAanKlikUit data."""
        if not self._aes_key or not encrypted_b64:
            return None
        
        try:
            aes_key = bytes.fromhex(self._aes_key)
            encrypted = base64.b64decode(encrypted_b64)
            
            # Use CBC mode with zero IV
            iv = b'\x00' * 16
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(encrypted) + decryptor.finalize()
            
            # Find JSON start
            json_start = -1
            for i in range(len(decrypted)):
                if decrypted[i:i+1] in [b'{', b'[']:
                    json_start = i
                    break
            
            if json_start == -1:
                return None
            
            json_bytes = decrypted[json_start:]
            
            # Remove PKCS7 padding if present
            if len(json_bytes) > 0:
                pad_len = json_bytes[-1]
                if isinstance(pad_len, int) and 0 < pad_len <= 16:
                    if all(b == pad_len for b in json_bytes[-pad_len:]):
                        json_bytes = json_bytes[:-pad_len]
            
            json_str = json_bytes.decode('utf-8', errors='ignore')
            
            # Find end of JSON
            depth = 0
            end_pos = 0
            for i, char in enumerate(json_str):
                if char in '{[':
                    depth += 1
                elif char in '}]':
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
            # Try to decrypt the 'data' field
            if 'data' in module_data and module_data['data']:
                decrypted = self._decrypt_kaku_data(module_data['data'])
                
                if decrypted and 'module' in decrypted:
                    module = decrypted['module']
                    
                    # Get module name
                    if 'name' in module and module['name']:
                        return module['name']
                    
                    # Get from entities
                    if 'entities' in module and module['entities']:
                        for entity in module['entities']:
                            if 'name' in entity and entity['name']:
                                return entity['name']
                    
                    # Try device field
                    if 'device' in module and module['device']:
                        return module['device']
            
            # Try status field
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
        """Guess device type from name."""
        name_lower = device_name.lower()
        
        if any(x in name_lower for x in ["motion", "sensor", "detector", "pir"]):
            return DEVICE_TYPE_SENSOR
        elif any(x in name_lower for x in ["dimmer", "dim", "brightness"]):
            return DEVICE_TYPE_DIMMER
        elif any(x in name_lower for x in ["lamp", "light", "bulb", "led"]):
            return DEVICE_TYPE_LIGHT
        elif any(x in name_lower for x in ["blind", "shutter", "curtain", "cover"]):
            return DEVICE_TYPE_COVER
        elif any(x in name_lower for x in ["plug", "socket", "outlet", "switch"]):
            return DEVICE_TYPE_SWITCH
        
        # Default based on value
        if device_value in [2, 4]:
            return DEVICE_TYPE_DIMMER
        
        return DEVICE_TYPE_SWITCH
    
    def _guess_if_dimmable(self, device_name: str, device_type: int) -> bool:
        """Guess if device is dimmable."""
        if device_type in [DEVICE_TYPE_DIMMER, DEVICE_TYPE_COVER]:
            return True
        
        name_lower = device_name.lower()
        return any(x in name_lower for x in ["dimmer", "dim", "brightness", "dimmable"])
    
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
                        
                        _LOGGER.info(f"✓ Authenticated successfully!")
                        self._connected = True
                        return True
                    else:
                        _LOGGER.error(f"Authentication failed: {result}")
        
        except Exception as e:
            _LOGGER.error(f"Authentication error: {e}")
        
        self._connected = False
        return False
    
    async def async_discover_devices(self) -> Dict[int, Dict[str, Any]]:
        """Discover devices with proper name extraction."""
        if not self._aes_key:
            _LOGGER.error("No AES key available")
            return self.devices
        
        _LOGGER.info("Discovering devices...")
        
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
                        _LOGGER.info(f"Found {len(sync_response)} modules")
                        
                        device_count = 0
                        
                        for module_data in sync_response:
                            module_id = int(module_data.get('id', 0))
                            
                            if module_id <= 0 or module_id in self.entity_blacklist:
                                continue
                            
                            # Store raw module data
                            self._raw_modules[module_id] = module_data
                            
                            # Extract the actual device name
                            device_name = self._extract_device_name(module_data)
                            
                            if not device_name:
                                device_name = f"Device {module_id}"
                                _LOGGER.debug(f"No name found for module {module_id}")
                            else:
                                _LOGGER.info(f"Found device: '{device_name}' (ID: {module_id})")
                            
                            # Determine device type
                            device_value = module_data.get('device', 0)
                            if isinstance(device_value, str) and device_value.isdigit():
                                device_value = int(device_value)
                            
                            device_type = self._guess_device_type(device_name, device_value)
                            is_dimmable = self._guess_if_dimmable(device_name, device_type)
                            
                            # Get state
                            current_state = False
                            version_status = module_data.get('version_status', '0')
                            if version_status and version_status != '0':
                                try:
                                    current_state = (int(version_status) % 2) == 1
                                except:
                                    pass
                            
                            # Create device
                            self.devices[module_id] = {
                                ATTR_DEVICE_ID: module_id,
                                ATTR_DEVICE_TYPE: device_type,
                                ATTR_DEVICE_MODEL: device_name,
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
                        
                        _LOGGER.info(f"✓ Created {device_count} devices")
                        
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
    
    async def async_turn_on(self, device_id: int) -> None:
        """Turn on a device."""
        _LOGGER.info(f"Turning on device {device_id}")
        # Implementation would go here
        if device_id in self.devices:
            self.devices[device_id]["state"] = True
    
    async def async_turn_off(self, device_id: int) -> None:
        """Turn off a device."""
        _LOGGER.info(f"Turning off device {device_id}")
        # Implementation would go here
        if device_id in self.devices:
            self.devices[device_id]["state"] = False
    
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
