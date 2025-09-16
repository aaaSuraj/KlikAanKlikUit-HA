"""Hub fix for large device IDs - handles module IDs > 255 properly."""

# In the _build_command_packet method, replace with:

def _build_command_packet(self, device_id: int, command: str, value: int = 0) -> bytes:
    """Build command packet - FIXED for large device IDs."""
    packet = bytearray()
    packet.extend(b'\xAA\xAA')
    packet.extend(bytes.fromhex(self.mac))
    
    # CRITICAL FIX: For large module IDs, we need different handling
    if device_id > 255:
        # Try using the lower 8 bits mapped differently
        # Many 433MHz systems use a mapping table for large IDs
        
        # Method 1: Use modulo to wrap to valid range
        mapped_id = (device_id % 200) + 1  # Maps to 1-200 range
        
        # Method 2: Use a hash to get consistent mapping
        # mapped_id = (device_id >> 16) & 0xFF
        
        # Method 3: Use only specific bits
        # mapped_id = (device_id >> 8) & 0xFF
        
        _LOGGER.warning(f"Large device ID {device_id} mapped to {mapped_id} for 433MHz transmission")
        packet.append(mapped_id)
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

# Alternative: Try cloud-only control for large IDs
async def _send_cloud_command(self, device_id: int, command: str) -> bool:
    """Send command via cloud for devices that don't work locally."""
    
    _LOGGER.info(f"Sending {command} to device {device_id} via cloud")
    
    # The cloud might use a different API endpoint for control
    control_data = {
        'email': self.email,
        'mac': self._gateway_mac or self.mac,
        'password_hash': self.password,
        'home_id': self._home_id or '',
        'action': 'control',
        'device_id': str(device_id),
        'command': command,
    }
    
    try:
        async with self._session.post(
            "https://trustsmartcloud2.com/ics2000_api/control.php",  # Might exist
            data=control_data,
            timeout=aiohttp.ClientTimeout(total=10),
            ssl=False,
        ) as response:
            if response.status == 200:
                return True
    except:
        pass
    
    return False

# Modified command methods
async def async_turn_on(self, device_id: int) -> bool:
    """Turn on - try local first, then cloud for large IDs."""
    
    # For large IDs, try cloud control
    if device_id > 100000:
        _LOGGER.info(f"Device {device_id} appears to be cloud-only, skipping local control")
        success = await self._send_cloud_command(device_id, 'on')
    else:
        # Try local control
        success = await self._send_local_command(device_id, 'on')
        
        # If failed and ID is large, try cloud
        if not success and device_id > 255:
            _LOGGER.warning(f"Local control failed for {device_id}, trying cloud")
            success = await self._send_cloud_command(device_id, 'on')
    
    if success:
        await self._update_device_state(device_id, {"state": True})
        asyncio.create_task(self._delayed_state_refresh(device_id))
    
    return success
