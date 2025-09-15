# KlikAanKlikUit ICS-2000 Integration for Home Assistant (Homebridge Compatible)

## Overview

This is a Home Assistant integration for the KlikAanKlikUit (Trust Smart Home) ICS-2000 gateway that is **100% compatible with the Homebridge plugin implementation**. It uses the exact same authentication methods and API endpoints as the Homebridge plugin.

## Key Features (Homebridge Compatible)

- ✅ **Homebridge-style authentication** - Sends your password in the `password_hash` field with an empty `mac`, matching the Homebridge plugin
- ✅ **gateway.php endpoint** - Uses the same device sync endpoint as Homebridge
- ✅ **Scene support** - Full support for ICS-2000 scenes
- ✅ **Color temperature lights** - Support for color temperature devices
- ✅ **Group devices** - Support for device groups
- ✅ **Entity blacklist** - Exclude specific entities like Homebridge
- ✅ **Daily sync schedule** - Automatic daily refresh at midnight
- ✅ **REST API server** - Optional REST server like Homebridge
- ✅ **Custom discovery messages** - Configurable discovery packets

## What's Different from Standard Integration?

### Authentication
- **Uses `password_hash` field**: Sends your plain password in the `password_hash` field with an empty `mac`
- **Uses `gateway.php`**: Fetches devices using the `gateway.php` endpoint like Homebridge

### API Endpoints
```python
# Homebridge-style endpoints
"https://trustsmartcloud2.com/ics2000_api/account.php"  # Login
"https://trustsmartcloud2.com/ics2000_api/gateway.php"  # Device sync
```

### Features from Homebridge
1. **Scenes**: Full scene support with activation
2. **Color Temperature**: Support for color temp lights (0-600 range)
3. **Groups**: Handle group devices correctly
4. **Entity Blacklist**: Exclude specific device IDs
5. **Daily Updates**: Automatic refresh at midnight
6. **Custom Discovery**: Configurable discovery messages

## Installation

### Method 1: Manual Installation
1. Copy all files to `custom_components/kaku_ics2000/` in your Home Assistant config directory
2. Restart Home Assistant
3. Add the integration through the UI

### Method 2: Replace Existing Integration
1. Backup your existing integration
2. Replace these key files with the Homebridge-compatible versions:
   - `hub.py` - Main hub with Homebridge authentication
   - `__init__.py` - Updated initialization with scene support
   - `scene.py` - New scene platform
   - `const.py` - Updated constants
   - `config_flow.py` - Updated configuration

## Configuration

### Initial Setup
1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "KlikAanKlikUit ICS-2000"
4. Enter your credentials:
   - **MAC Address**: Your ICS-2000 MAC address
   - **Email**: Your KlikAanKlikUit account email
   - **Password**: Your account password
   - **IP Address** (optional): Static IP if known
   - **Name** (optional): Custom name for the hub

### Options (Homebridge Features)
- **Show Scenes**: Enable/disable scene entities
- **Entity Blacklist**: Comma-separated list of entity IDs to exclude
- **Custom Discovery Message**: Custom UDP discovery packet
- **Start REST Server**: Enable REST API server
- **REST Server Port**: Port for REST API (default: 9100)

## Supported Devices

### Standard Devices
- ✅ Lights (on/off)
- ✅ Dimmable lights
- ✅ Color temperature lights
- ✅ Switches
- ✅ Smart plugs
- ✅ Covers/blinds
- ✅ Sensors
- ✅ Groups

### Special Features
- **Scenes**: Activate pre-configured scenes
- **Groups**: Control multiple devices as one
- **Color Temperature**: Adjust warmth of compatible lights

## Services

### kaku_ics2000.reload
Reload the integration (like Homebridge reload switch)
```yaml
service: kaku_ics2000.reload
```

### kaku_ics2000.run_scene
Run a specific scene
```yaml
service: kaku_ics2000.run_scene
data:
  scene_id: 123
```

### kaku_ics2000.identify
Make a device flash for identification
```yaml
service: kaku_ics2000.identify
data:
  device_id: 5
```

### kaku_ics2000.refresh_devices
Refresh device list from cloud
```yaml
service: kaku_ics2000.refresh_devices
```

## Differences from Standard HA Integration

| Feature | Standard Integration | Homebridge Compatible |
|---------|---------------------|----------------------|
| Auth Field | 'password' | `password_hash` ✅ |
| Sync Endpoint | /devices | /gateway.php ✅ |
| Scenes | ❌ | ✅ |
| Color Temp | Limited | Full (0-600) ✅ |
| Groups | Basic | Full support ✅ |
| Entity Blacklist | ❌ | ✅ |
| REST API | ❌ | Optional ✅ |
| Daily Sync | ❌ | Midnight ✅ |

## Troubleshooting

### Authentication Fails
- The integration uses the **`password_hash`** field with your plain password like Homebridge
- Ensure your email and password are correct
- MAC address should be in format: AA:BB:CC:DD:EE:FF

### Devices Not Found
- Check if gateway.php endpoint is accessible
- Debug logs include the gateway.php URL; enable debug logging to verify cloud sync
- Try manual IP address entry
- Check entity blacklist settings

### Scenes Not Showing
- Enable "Show Scenes" in integration options
- Refresh devices after enabling

## Technical Details

### Homebridge Authentication Format
```python
# Login request mirrors Homebridge plugin
login_data = {
    'action': 'login',
    'email': email,
    'password_hash': password,
    'device_unique_id': 'android',
    'platform': '',
    'mac': '',
}
```

### Device Sync
```python
# Uses Homebridge gateway.php endpoint
sync_data = {
    'email': email,
    'mac': mac,
    'action': 'sync',
    'password_hash': password,
}
response = await session.post(
    "https://trustsmartcloud2.com/ics2000_api/gateway.php",
    data=sync_data
)
```

## Credits

This integration is based on:
- The Homebridge plugin structure and authentication method
- Home Assistant integration framework

## License

MIT License - Same as the original integrations

## Support

For issues or questions:
1. Check the Homebridge plugin for reference behavior
2. Enable debug logging for detailed information
3. Report issues with debug logs

## Version History

### 1.0.0 - Homebridge Compatible
- Initial release with full Homebridge compatibility
- Implemented Homebridge-style authentication using `password_hash`
- Added gateway.php endpoint support
- Full scene support
- Color temperature support
- Group device support
- Entity blacklist
- Daily sync schedule
- Optional REST API server
