"""Light platform for KlikAanKlikUit ICS-2000 - FIXED with proper device names."""

from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    ATTR_CONFIDENCE,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_MODEL,
    ATTR_DEVICE_TYPE,
    ATTR_DIMMABLE,
    ATTR_LAST_COMMAND,
    ATTR_LAST_UPDATE,
    ATTR_ZIGBEE,
    DEVICE_TYPE_DIMMER,
    DEVICE_TYPE_LIGHT,
    DOMAIN,
)
from .hub import ICS2000Hub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KlikAanKlikUit lights - only for actual light devices."""
    
    data = hass.data[DOMAIN][config_entry.entry_id]
    hub: ICS2000Hub = data["hub"]
    coordinator: DataUpdateCoordinator = data["coordinator"]
    
    # Create light entities ONLY for light/dimmer type devices
    entities = []
    for device in hub.get_all_devices():
        device_type = device.get(ATTR_DEVICE_TYPE)
        device_id = device[ATTR_DEVICE_ID]
        device_name = device.get(ATTR_DEVICE_MODEL, f"Device {device_id}")
        
        # Only create lights for actual light/dimmer devices
        if device_type in [DEVICE_TYPE_LIGHT, DEVICE_TYPE_DIMMER]:
            if device.get(ATTR_DIMMABLE, False):
                entities.append(
                    KakuDimmableLight(
                        coordinator,
                        hub,
                        device_id,
                        config_entry.entry_id,
                    )
                )
                _LOGGER.info(f"Created dimmable light for {device_name} (ID: {device_id})")
            else:
                entities.append(
                    KakuLight(
                        coordinator,
                        hub,
                        device_id,
                        config_entry.entry_id,
                    )
                )
                _LOGGER.info(f"Created light for {device_name} (ID: {device_id})")
    
    if entities:
        async_add_entities(entities)
        _LOGGER.info(f"Added {len(entities)} light entities")


class KakuLight(CoordinatorEntity, LightEntity):
    """KlikAanKlikUit Light."""
    
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        hub: ICS2000Hub,
        device_id: int,
        config_entry_id: str,
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        
        self._hub = hub
        self._device_id = device_id
        self._config_entry_id = config_entry_id
        
        # Get device info from hub
        self._device = hub.get_device(device_id) or {}
        
        # Set unique ID
        self._attr_unique_id = f"{hub.mac}_{device_id}"
        
        # Use the actual device name from the hub!
        device_name = self._device.get(ATTR_DEVICE_MODEL, f"Light {device_id}")
        self._attr_name = device_name
        
        # Set device info with proper name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{hub.mac}_{device_id}")},
            name=device_name,
            manufacturer="KlikAanKlikUit",
            model=self._device.get(ATTR_DEVICE_MODEL, "Light"),
            via_device=(DOMAIN, hub.mac),
        )
        
        # We have real state tracking now!
        self._attr_assumed_state = False
        
        # Set supported features
        self._setup_features()
    
    def _setup_features(self) -> None:
        """Set up supported features."""
        # Basic on/off mode
        self._attr_supported_color_modes = {ColorMode.ONOFF}
        self._attr_color_mode = ColorMode.ONOFF
        
        # Features
        self._attr_supported_features = LightEntityFeature.EFFECT
        self._attr_effect_list = ["identify"]
    
    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        device = self._hub.get_device(self._device_id)
        return device.get("state", False) if device else False
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._hub.connected
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        device = self._hub.get_device(self._device_id)
        if not device:
            return {}
        
        attributes = {
            ATTR_DEVICE_ID: self._device_id,
            ATTR_DEVICE_TYPE: device.get(ATTR_DEVICE_TYPE),
            ATTR_DEVICE_MODEL: device.get(ATTR_DEVICE_MODEL),
            ATTR_ZIGBEE: device.get(ATTR_ZIGBEE, False),
            ATTR_DIMMABLE: device.get(ATTR_DIMMABLE, False),
            "real_state": True,  # We have real state tracking!
        }
        
        # Add state tracking info
        if ATTR_LAST_COMMAND in device:
            attributes[ATTR_LAST_COMMAND] = device[ATTR_LAST_COMMAND]
        if ATTR_LAST_UPDATE in device:
            attributes[ATTR_LAST_UPDATE] = device[ATTR_LAST_UPDATE]
        if ATTR_CONFIDENCE in device:
            attributes[ATTR_CONFIDENCE] = f"{device[ATTR_CONFIDENCE]}%"
        
        # Add version info
        if "version_status" in device:
            attributes["version_status"] = device["version_status"]
        if "version_data" in device:
            attributes["version_data"] = device["version_data"]
        
        return attributes
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        await self._hub.async_turn_on(self._device_id)
        
        # Request coordinator refresh
        await self.coordinator.async_request_refresh()
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self._hub.async_turn_off(self._device_id)
        
        # Request coordinator refresh
        await self.coordinator.async_request_refresh()
    
    async def async_set_effect(self, effect: str) -> None:
        """Set effect."""
        if effect == "identify":
            await self._hub.async_identify_device(self._device_id)


class KakuDimmableLight(KakuLight):
    """KlikAanKlikUit Dimmable Light."""
    
    def _setup_features(self) -> None:
        """Set up supported features for dimmable light."""
        # Brightness mode
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.BRIGHTNESS
        
        # Features
        self._attr_supported_features = LightEntityFeature.EFFECT
        self._attr_effect_list = ["identify"]
    
    @property
    def brightness(self) -> Optional[int]:
        """Return brightness (0-255 for HA)."""
        device = self._hub.get_device(self._device_id)
        if device and device.get("brightness") is not None:
            brightness = device["brightness"]
            # Convert 0-100 to 0-255 for HA
            if brightness <= 100:
                return int((brightness / 100) * 255)
            else:
                return brightness
        
        return 255 if self.is_on else 0
    
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light with optional brightness."""
        if ATTR_BRIGHTNESS in kwargs:
            # Convert 0-255 to 0-100 for the hub
            brightness = int((kwargs[ATTR_BRIGHTNESS] / 255) * 100)
            await self._hub.async_set_brightness(self._device_id, brightness)
        else:
            await self._hub.async_turn_on(self._device_id)
        
        # Request coordinator refresh
        await self.coordinator.async_request_refresh()