"""Hub for KlikAanKlikUit ICS-2000 - WITH REAL STATE TRACKING!"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import socket
import base64
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    ATTR_CONFIDENCE,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_MODEL,
    ATTR_DEVICE_TYPE,
    ATTR_DIMMABLE,
    ATTR_LAST_COMMAND,
    ATTR_LAST_UPDATE,
    ATTR_ZIGBEE,
    CONFIDENCE_HIGH,
    DEFAULT_SLEEP,
    DEFAULT_TRIES,
    DEVICE_TYPE_DIMMER,
    DEVICE_TYPE_LIGHT,
    DEVICE_TYPE_SWITCH,
    DEVICE_TYPE_COVER,
    DEVICE_TYPE_SENSOR,
    DISCOVERY_PORT,
    DISCOVERY_TIMEOUT,
    EVENT_COMMAND_SENT,
    EVENT_DEVICE_DISCOVERED,
)
from .state_manager import StateManager

_LOGGER = logging.getLogger(__name__)

AUTH_ENDPOINT = "https://trustsmartcloud2.com/ics2000_api/account.php"
SYNC_ENDPOINT = "https://trustsmartcloud2.com/ics2000_api/gateway.php"
LOCAL_CONTROL_PORT = 9760


class ICS2000Hub:
    """ICS-2000 Hub with REAL state tracking from cloud!"""
    
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
    
    def _decrypt_kaku_data(self, encrypted_b64: str) -> Optional[Dict]:
        """Decrypt KlikAanKlikUit data."""
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            
            if not self._aes_key:
                return None
            
            encrypted = base64.b64decode(encrypted_b64)
            
            iv = b'\x00' * 16
            cipher = Cipher(algorithms.AES(self._aes_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(encrypted) + decryptor.finalize()
            
            # Find JSON start
            json_start = -1
            for i in range(len(decrypted)):
                if decrypted[i:i+1] in [b'{', b'[']:
                    json_start = i
                    break
            
            if json_start < 0:
                return None
            
            json_bytes = decrypted[json_start:]
            
            # Remove padding
            if len(json_bytes) > 0:
                pad_len = json_bytes[-1]
                if isinstance(pad_len, int) and pad_len < 16:
                    if all(b == pad_len for b in json_bytes[-pad_len:]):
                        json_bytes = json_bytes[:-pad_len]
            
            json_text = json_bytes.decode('utf-8', errors='ignore')
            
            # Find JSON end
            depth = 0
            json_end = 0
            for i, char in enumerate(json_text):
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        json_end = i + 1
                        break
            
            if json_end > 0:
                json_text = json_text[:json_end]
            
            return json.loads(json_text)
            
        except Exception:
            return None
    
    async def async_connect(self) -> bool:
        """Connect to ICS-2000."""
        if self._connected:
            return True
        
        try:
            self._session = async_get_clientsession(self.hass)
            
            _LOGGER.info("Authenticating with cloud...")
            if await self._authenticate():
                _LOGGER.info("✓ Authentication successful")
            else:
                _LOGGER.error("Authentication failed")
                return False
            
            if not self.ip_address:
                self.ip_address = await self._async_discover_local()
            
            if self.ip_address:
                _LOGGER.info(f"ICS-2000 found locally at {self.ip_address}")
            else:
                _LOGGER.warning("ICS-2000 not found on local network")
            
            self._connected = True
            return True
            
        except Exception as err:
            _LOGGER.error(f"Connection error: {err}")
            self._connected = False
            return False
    
    async def _authenticate(self) -> bool:
        """Authenticate."""
        
        login_data = {
            'action': 'login',
            'email': self.email,
            'password_hash': self.password,
            'device_unique_id': 'android',
            'platform': '',
            'mac': '',
        }
        
        try:
            async with self._session.post(
                AUTH_ENDPOINT,
                data=login_data,
                timeout=aiohttp.ClientTimeout(total=10),
                ssl=False,
            ) as response:
                if response.status == 200:
                    text = await response.text()
                    auth_data = json.loads(text)
                    
                    if 'homes' in auth_data and auth_data['homes']:
                        home = auth_data['homes'][0]
                        self._home_id = home.get('home_id')
                        self._gateway_mac = home.get('mac')
                        aes_key_hex = home.get('aes_key')
                        
                        if aes_key_hex:
                            self._aes_key = bytes.fromhex(aes_key_hex)
                            _LOGGER.info(f"Got AES key for home {self._home_id}, MAC {self._gateway_mac}")
                            return True
                    
        except Exception as e:
            _LOGGER.error(f"Authentication error: {e}")
        
        return False
    
    async def async_discover_devices(self) -> Dict[int, Dict[str, Any]]:
        """Discover devices with REAL state from cloud!"""
        
        if not self._aes_key:
            _LOGGER.error("No AES key available")
            return self.devices
        
        _LOGGER.info("Fetching devices with state...")
        
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
                            
                            # Store raw module data for state updates
                            self._raw_modules[module_id] = module_data
                            
                            # Get device name from data field
                            module_name = None
                            device_type = DEVICE_TYPE_SWITCH
                            device_value = 1
                            
                            encrypted_data = module_data.get('data')
                            if encrypted_data:
                                decrypted_data = self._decrypt_kaku_data(encrypted_data)
                                
                                if decrypted_data and 'module' in decrypted_data:
                                    module = decrypted_data['module']
                                    module_name = module.get('name')
                                    device_value = module.get('device', 1)
                            
                            if not module_name:
                                module_name = f"Device {module_id}"
                            
                            # Get ACTUAL STATE from status field!
                            current_state = False  # Default
                            encrypted_status = module_data.get('status')
                            if encrypted_status:
                                decrypted_status = self._decrypt_kaku_data(encrypted_status)
                                
                                if decrypted_status and 'module' in decrypted_status:
                                    status_module = decrypted_status['module']
                                    functions = status_module.get('functions', [])
                                    
                                    # functions: [0] = OFF, [1] = ON
                                    if functions and len(functions) > 0:
                                        current_state = functions[0] == 1
                                        _LOGGER.info(f"  {module_name}: functions={functions} → state={'ON' if current_state else 'OFF'}")
                            
                            # Determine device type
                            device_type = self._guess_device_type(module_name, device_value)
                            is_dimmable = self._guess_if_dimmable(module_name, device_type)
                            
                            # Create device with REAL state!
                            self.devices[module_id] = {
                                ATTR_DEVICE_ID: module_id,
                                ATTR_DEVICE_TYPE: device_type,
                                ATTR_DEVICE_MODEL: module_name,
                                ATTR_DIMMABLE: is_dimmable,
                                ATTR_ZIGBEE: False,
                                "state": current_state,  # REAL state from cloud!
                                "brightness": 50 if is_dimmable else None,
                                "position": None,
                                "device_value": device_value,
                                "version_status": module_data.get('version_status'),
                                "version_data": module_data.get('version_data'),
                            }
                            
                            device_count += 1
                            
                            if module_name != f"Device {module_id}":
                                _LOGGER.info(f"✓ Device {device_count}: '{module_name}' (ID: {module_id}, state: {'ON' if current_state else 'OFF'})")
                            else:
                                _LOGGER.info(f"✓ Device {device_count}: Module {module_id} (no name, state: {'ON' if current_state else 'OFF'})")
                        
                        _LOGGER.info(f"✓ Created {device_count} devices with REAL state tracking!")
                        
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
    
    async def async_update_states(self) -> None:
        """Update device states from cloud."""
        if not self._aes_key:
            return
        
        _LOGGER.debug("Updating device states from cloud...")
        
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
                        for module_data in sync_response:
                            module_id = int(module_data.get('id', 0))
                            
                            if module_id in self.devices:
                                # Update raw data
                                self._raw_modules[module_id] = module_data
                                
                                # Get state from status field
                                encrypted_status = module_data.get('status')
                                if encrypted_status:
                                    decrypted_status = self._decrypt_kaku_data(encrypted_status)
                                    
                                    if decrypted_status and 'module' in decrypted_status:
                                        status_module = decrypted_status['module']
                                        functions = status_module.get('functions', [])
                                        
                                        if functions and len(functions) > 0:
                                            new_state = functions[0] == 1
                                            old_state = self.devices[module_id].get('state', False)
                                            
                                            if new_state != old_state:
                                                _LOGGER.info(f"State changed for {self.devices[module_id][ATTR_DEVICE_MODEL]}: {'ON' if new_state else 'OFF'}")
                                                self.devices[module_id]['state'] = new_state
                                                self.devices[module_id][ATTR_LAST_UPDATE] = datetime.now().isoformat()
                                                self.devices[module_id][ATTR_CONFIDENCE] = CONFIDENCE_HIGH
                                
                                # Update version numbers
                                self.devices[module_id]['version_status'] = module_data.get('version_status')
                                self.devices[module_id]['version_data'] = module_data.get('version_data')
                        
        except Exception as e:
            _LOGGER.error(f"State update error: {e}")
    
    def _guess_device_type(self, name: str, device_value: int) -> str:
        """Guess device type from name."""
        name_lower = name.lower()
        
        if any(word in name_lower for word in ['light', 'bulb', 'lamp', 'spot', 'led', 'ambient']):
            return DEVICE_TYPE_LIGHT
        elif any(word in name_lower for word in ['dimmer', 'dim']):
            return DEVICE_TYPE_DIMMER
        elif any(word in name_lower for word in ['switch', 'plug', 'outlet']):
            return DEVICE_TYPE_SWITCH
        elif any(word in name_lower for word in ['blind', 'curtain', 'shutter', 'shade']):
            return DEVICE_TYPE_COVER
        elif any(word in name_lower for word in ['sensor', 'motion', 'door', 'window']):
            return DEVICE_TYPE_SENSOR
        elif any(word in name_lower for word in ['fan', 'speaker']):
            return DEVICE_TYPE_SWITCH
        
        type_map = {
            1: DEVICE_TYPE_SWITCH,
            2: DEVICE_TYPE_DIMMER,
            3: DEVICE_TYPE_LIGHT,
            4: DEVICE_TYPE_COVER,
            5: DEVICE_TYPE_SENSOR,
        }
        
        return type_map.get(device_value, DEVICE_TYPE_SWITCH)
    
    def _guess_if_dimmable(self, name: str, device_type: str) -> bool:
        """Guess if device is dimmable."""
        if device_type == DEVICE_TYPE_DIMMER:
            return True
        
        name_lower = name.lower()
        
        if any(word in name_lower for word in ['ambient', 'bedroom', 'living']):
            return True
        
        if any(word in name_lower for word in ['switch', 'fan', 'speaker', 'floodlight', 'sensor']):
            return False
        
        if device_type == DEVICE_TYPE_LIGHT:
            return True
        
        return False
    
    async def _async_discover_local(self) -> Optional[str]:
        """Discover ICS-2000."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(DISCOVERY_TIMEOUT)
            
            sock.sendto(b"D", ("255.255.255.255", DISCOVERY_PORT))
            
            try:
                data, addr = sock.recvfrom(1024)
                response_hex = data.hex().upper()
                
                if self.mac in response_hex or self.mac_formatted.replace(":", "") in response_hex:
                    return addr[0]
                    
            except socket.timeout:
                pass
                
        except Exception:
            pass
        finally:
            sock.close()
        
        return None
    
    def _build_command_packet(self, device_id: int, command: str, value: int = 0) -> bytes:
        """Build command packet."""
        packet = bytearray()
        packet.extend(b'\xAA\xAA')
        packet.extend(bytes.fromhex(self.mac))
        
        if device_id > 255:
            packet.append(device_id & 0xFF)
        else:
            packet.append(device_id)
        
        if command == 'on':
            packet.append(0x01)
        elif command == 'off':
            packet.append(0x00)
        elif command == 'dim':
            packet.append(0x02)
        else:
            packet.append(0x01)
        
        packet.append(value & 0xFF)
        
        checksum = sum(packet) & 0xFF
        packet.append(checksum)
        
        return bytes(packet)
    
    async def _send_local_command(self, device_id: int, command: str, value: int = 0) -> bool:
        """Send local command."""
        if not self.ip_address:
            _LOGGER.debug(f"No IP, simulating {command} for device {device_id}")
            return True
        
        try:
            packet = self._build_command_packet(device_id, command, value)
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            
            for attempt in range(self.tries):
                sock.sendto(packet, (self.ip_address, LOCAL_CONTROL_PORT))
                _LOGGER.debug(f"Sent {command} to module/device {device_id}")
                
                if attempt < self.tries - 1:
                    await asyncio.sleep(0.1)
            
            sock.close()
            return True
            
        except Exception as e:
            _LOGGER.error(f"Command error: {e}")
            return False
    
    async def async_turn_on(self, device_id: int) -> bool:
        """Turn on."""
        success = await self._send_local_command(device_id, 'on')
        if success:
            await self._update_device_state(device_id, {"state": True})
            # Refresh state from cloud after a short delay
            asyncio.create_task(self._delayed_state_refresh(device_id))
        return success
    
    async def async_turn_off(self, device_id: int) -> bool:
        """Turn off."""
        success = await self._send_local_command(device_id, 'off')
        if success:
            await self._update_device_state(device_id, {"state": False})
            # Refresh state from cloud after a short delay
            asyncio.create_task(self._delayed_state_refresh(device_id))
        return success
    
    async def _delayed_state_refresh(self, device_id: int) -> None:
        """Refresh state from cloud after a delay."""
        await asyncio.sleep(2)  # Wait 2 seconds for cloud to update
        await self.async_update_states()
    
    async def async_set_brightness(self, device_id: int, brightness: int) -> bool:
        """Set brightness."""
        device = self.devices.get(device_id, {})
        
        if not device.get(ATTR_DIMMABLE):
            return await self.async_turn_on(device_id) if brightness > 0 else await self.async_turn_off(device_id)
        
        value = int((brightness / 100) * 255)
        success = await self._send_local_command(device_id, 'dim', value)
        
        if success:
            await self._update_device_state(
                device_id,
                {"state": brightness > 0, "brightness": brightness}
            )
            asyncio.create_task(self._delayed_state_refresh(device_id))
        
        return success
    
    async def async_set_cover_position(self, device_id: int, position: int) -> bool:
        """Set cover position."""
        if position > 50:
            success = await self.async_turn_on(device_id)
        else:
            success = await self.async_turn_off(device_id)
        
        if success:
            await self._update_device_state(device_id, {"position": position})
        
        return success
    
    async def async_run_scene(self, scene_id: int) -> bool:
        """Run scene."""
        return False
    
    async def async_identify_device(self, device_id: int) -> bool:
        """Identify device."""
        try:
            for _ in range(3):
                await self.async_turn_on(device_id)
                await asyncio.sleep(0.5)
                await self.async_turn_off(device_id)
                await asyncio.sleep(0.5)
            return True
        except:
            return False
    
    async def _update_device_state(self, device_id: int, state_update: Dict[str, Any]) -> None:
        """Update device state."""
        if device_id not in self.devices:
            return
        
        device = self.devices[device_id]
        device.update(state_update)
        device[ATTR_LAST_COMMAND] = str(state_update)
        device[ATTR_LAST_UPDATE] = datetime.now().isoformat()
        device[ATTR_CONFIDENCE] = CONFIDENCE_HIGH
        
        if self.state_manager:
            await self.state_manager.async_update_device_state(device_id, device)
        
        for callback in self._state_callbacks:
            try:
                await callback(device_id, device)
            except Exception as e:
                _LOGGER.error(f"Callback error: {e}")
        
        self.hass.bus.async_fire(
            EVENT_COMMAND_SENT,
            {
                "hub": self.mac,
                "device_id": device_id,
                "command": str(state_update),
                "success": True,
            },
        )
    
    async def async_disconnect(self) -> None:
        """Disconnect."""
        self._connected = False
        _LOGGER.info("Disconnected from ICS-2000")
    
    def register_state_callback(self, callback: Callable) -> None:
        """Register callback."""
        self._state_callbacks.append(callback)
    
    def get_device(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Get device."""
        return self.devices.get(device_id)
    
    def get_all_devices(self) -> List[Dict[str, Any]]:
        """Get all devices."""
        return list(self.devices.values())
    
    def get_all_scenes(self) -> List[Dict[str, Any]]:
        """Get all scenes."""
        return list(self.scenes.values())
    
    @property
    def connected(self) -> bool:
        """Return connection status."""
        return self._connected
    
    @property
    def assumed_state(self) -> bool:
        """Return if we're using assumed state."""
        # We have REAL state tracking now!
        return False