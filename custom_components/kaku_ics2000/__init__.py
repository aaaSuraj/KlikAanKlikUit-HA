"""The KlikAanKlikUit ICS-2000 integration - Homebridge Compatible."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_EMAIL,
    CONF_IP_ADDRESS,
    CONF_MAC,
    CONF_PASSWORD,
    Platform,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.event import async_track_time_change

from .const import (
    CONF_AES_KEY,
    CONF_DEVICE_DISCOVERY,
    CONF_ENTITY_BLACKLIST,
    CONF_MQTT_ENABLE,
    CONF_MQTT_TOPIC,
    CONF_SHOW_SCENES,
    CONF_STATE_RESTORE,
    CONF_TRIES,
    CONF_SLEEP,
    DEFAULT_MQTT_TOPIC,
    DEFAULT_TRIES,
    DEFAULT_SLEEP,
    DEFAULT_SHOW_SCENES,
    DOMAIN,
    SERVICE_IDENTIFY,
    SERVICE_REFRESH_DEVICES,
    SERVICE_RESET_STATE,
    SERVICE_RELOAD,
)
from .hub import ICS2000Hub
from .state_manager import StateManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.COVER,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SCENE,  # Added scene support like Homebridge
]

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}_states"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up KlikAanKlikUit ICS-2000 from a config entry - Homebridge Compatible."""
    
    hass.data.setdefault(DOMAIN, {})
    
    # Initialize state storage
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    state_manager = StateManager(hass, store)
    await state_manager.async_load()
    
    # Get entity blacklist from options (like Homebridge)
    entity_blacklist = entry.options.get(CONF_ENTITY_BLACKLIST, [])
    
    # Create hub instance with Homebridge-style configuration
    hub = ICS2000Hub(
        hass=hass,
        mac=entry.data[CONF_MAC],
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        ip_address=entry.data.get(CONF_IP_ADDRESS),
        aes_key=entry.data.get(CONF_AES_KEY),
        tries=entry.options.get(CONF_TRIES, DEFAULT_TRIES),
        sleep=entry.options.get(CONF_SLEEP, DEFAULT_SLEEP),
        state_manager=state_manager,
    )
    
    # Set entity blacklist
    hub.entity_blacklist = entity_blacklist
    
    # Try to connect using Homebridge-style authentication
    try:
        await hub.async_connect()
        await hub.async_discover_devices()
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to connect to ICS-2000: {err}") from err
    
    # Create update coordinator
    async def async_update_data():
        """Fetch data from ICS-2000."""
        try:
            # Update device states
            await hub.async_update_states()
            return {"devices": hub.devices, "scenes": hub.scenes}
        except Exception as err:
            raise UpdateFailed(f"Error communicating with ICS-2000: {err}")
    
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"ICS-2000 ({entry.data[CONF_MAC]})",
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
    )
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    # Store hub and coordinator
    hass.data[DOMAIN][entry.entry_id] = {
        "hub": hub,
        "coordinator": coordinator,
        "state_manager": state_manager,
    }
    
    # Register device
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, hub.mac)},
        manufacturer="KlikAanKlikUit",
        model="ICS-2000",
        name=f"ICS-2000 ({hub.mac[-6:]})",
        sw_version=hub.firmware_version,
    )
    
    # Forward setup to platforms
    platforms_to_setup = PLATFORMS.copy()
    
    # Only setup scene platform if enabled (like Homebridge showScenes option)
    if not entry.options.get(CONF_SHOW_SCENES, DEFAULT_SHOW_SCENES):
        platforms_to_setup.remove(Platform.SCENE)
    
    await hass.config_entries.async_forward_entry_setups(entry, platforms_to_setup)
    
    # Register services
    await async_register_services(hass, entry)
    
    # Setup MQTT publishing if enabled
    if entry.options.get(CONF_MQTT_ENABLE, False):
        await setup_mqtt_publishing(hass, entry, hub)
    
    # Schedule daily updates (like Homebridge)
    async def scheduled_update():
        """Daily update of AES key and local IP."""
        _LOGGER.info("Running scheduled daily update (Homebridge-style)")
        await hub.async_connect()
        await hub.async_discover_devices()
        await coordinator.async_request_refresh()
    
    # Schedule daily update at midnight
    entry.async_on_unload(
        async_track_time_change(
            hass, scheduled_update, hour=0, minute=0, second=0
        )
    )
    
    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    
    # Determine which platforms to unload
    platforms_to_unload = PLATFORMS.copy()
    if not entry.options.get(CONF_SHOW_SCENES, DEFAULT_SHOW_SCENES):
        platforms_to_unload.remove(Platform.SCENE)
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms_to_unload)
    
    if unload_ok:
        # Save final states
        data = hass.data[DOMAIN][entry.entry_id]
        await data["state_manager"].async_save()
        
        # Disconnect hub
        await data["hub"].async_disconnect()
        
        # Remove data
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_register_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register services for the integration."""
    
    async def handle_identify(call: ServiceCall) -> None:
        """Handle identify service call."""
        device_id = call.data.get("device_id")
        data = hass.data[DOMAIN][entry.entry_id]
        hub = data["hub"]
        await hub.async_identify_device(device_id)
    
    async def handle_refresh_devices(call: ServiceCall) -> None:
        """Handle refresh devices service call."""
        data = hass.data[DOMAIN][entry.entry_id]
        hub = data["hub"]
        await hub.async_discover_devices()
        await data["coordinator"].async_request_refresh()
    
    async def handle_reset_state(call: ServiceCall) -> None:
        """Handle reset state service call."""
        device_id = call.data.get("device_id")
        data = hass.data[DOMAIN][entry.entry_id]
        state_manager = data["state_manager"]
        
        if device_id:
            await state_manager.async_reset_device_state(device_id)
        else:
            await state_manager.async_reset_all_states()
    
    async def handle_reload(call: ServiceCall) -> None:
        """Handle reload service call (like Homebridge reload switch)."""
        data = hass.data[DOMAIN][entry.entry_id]
        hub = data["hub"]
        
        # Re-run setup
        await hub.async_connect()
        await hub.async_discover_devices()
        await data["coordinator"].async_request_refresh()
        
        _LOGGER.info("Reloaded ICS-2000 integration")
    
    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_IDENTIFY,
        handle_identify,
        schema=vol.Schema({
            vol.Required("device_id"): vol.Coerce(int),
        }),
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_DEVICES,
        handle_refresh_devices,
    )
    
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_STATE,
        handle_reset_state,
        schema=vol.Schema({
            vol.Optional("device_id"): vol.Coerce(int),
        }),
    )
    
    # Add reload service (like Homebridge reload switch)
    hass.services.async_register(
        DOMAIN,
        SERVICE_RELOAD,
        handle_reload,
    )


async def setup_mqtt_publishing(
    hass: HomeAssistant,
    entry: ConfigEntry,
    hub: ICS2000Hub,
) -> None:
    """Setup MQTT state publishing."""
    
    # Check if MQTT is available
    mqtt_available = False
    
    try:
        if "mqtt" in hass.config.components:
            mqtt_available = True
    except Exception as err:
        _LOGGER.debug(f"MQTT check failed: {err}")
    
    if not mqtt_available:
        _LOGGER.warning("MQTT not configured, skipping MQTT publishing")
        return
    
    base_topic = entry.options.get(CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC)
    
    # Subscribe to state changes
    async def state_changed(device_id: int, state: dict) -> None:
        """Publish state changes to MQTT."""
        topic = f"{base_topic}/{hub.mac}/{device_id}/state"
        payload = json.dumps({
            "device_id": device_id,
            "state": state.get("state", "unknown"),
            "brightness": state.get("brightness"),
            "position": state.get("position"),
            "color_temperature": state.get("color_temperature"),
            "last_command": state.get("last_command"),
            "last_update": state.get("last_update"),
            "confidence": state.get("confidence", 90),
        })
        
        try:
            await hass.services.async_call(
                "mqtt",
                "publish",
                {
                    "topic": topic,
                    "payload": payload,
                    "retain": True,
                },
                blocking=False,
            )
            _LOGGER.debug(f"Published state to MQTT: {topic}")
        except Exception as err:
            _LOGGER.error(f"Failed to publish to MQTT: {err}")
    
    # Register callback
    hub.register_state_callback(state_changed)
