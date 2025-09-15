"""Switch platform for KlikAanKlikUit ICS-2000 - FIXED with proper device names."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
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
    ATTR_LAST_COMMAND,
    ATTR_LAST_UPDATE,
    ATTR_ZIGBEE,
    DEVICE_TYPE_SWITCH,
    DOMAIN,
)
from .hub import ICS2000Hub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KlikAanKlikUit switches."""
    
    data = hass.data[DOMAIN][config_entry.entry_id]
    hub: ICS2000Hub = data["hub"]
    coordinator: DataUpdateCoordinator = data["coordinator"]
    
    # Create switch entities only for switch-type devices
    entities = []
    for device in hub.get_all_devices():
        # Only create switches for actual switch devices
        if device.get(ATTR_DEVICE_TYPE) == DEVICE_TYPE_SWITCH:
            entities.append(
                KakuSwitch(
                    coordinator,
                    hub,
                    device[ATTR_DEVICE_ID],
                    config_entry.entry_id,
                )
            )
            _LOGGER.info(f"Created switch entity for {device[ATTR_DEVICE_MODEL]} (ID: {device[ATTR_DEVICE_ID]})")
    
    if entities:
        async_add_entities(entities)
        _LOGGER.info(f"Added {len(entities)} switch entities")


class KakuSwitch(CoordinatorEntity, SwitchEntity):
    """KlikAanKlikUit Switch."""
    
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        hub: ICS2000Hub,
        device_id: int,
        config_entry_id: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        
        self._hub = hub
        self._device_id = device_id
        self._config_entry_id = config_entry_id
        
        # Get device info from hub
        self._device = hub.get_device(device_id) or {}
        
        # Set unique ID
        self._attr_unique_id = f"{hub.mac}_{device_id}"
        
        # Use the actual device name from the hub!
        device_name = self._device.get(ATTR_DEVICE_MODEL, f"Device {device_id}")
        self._attr_name = device_name
        
        # Determine device class based on name
        model_lower = device_name.lower()
        if "plug" in model_lower:
            self._attr_device_class = SwitchDeviceClass.OUTLET
        elif "fan" in model_lower:
            self._attr_device_class = SwitchDeviceClass.SWITCH
        elif "speaker" in model_lower:
            self._attr_device_class = SwitchDeviceClass.SWITCH
        else:
            self._attr_device_class = SwitchDeviceClass.SWITCH
        
        # Set device info with proper name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{hub.mac}_{device_id}")},
            name=device_name,
            manufacturer="KlikAanKlikUit",
            model=self._device.get(ATTR_DEVICE_MODEL, "Switch"),
            via_device=(DOMAIN, hub.mac),
        )
        
        # We have real state tracking now!
        self._attr_assumed_state = False
    
    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
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
        """Turn on the switch."""
        await self._hub.async_turn_on(self._device_id)
        
        # Request coordinator refresh
        await self.coordinator.async_request_refresh()
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self._hub.async_turn_off(self._device_id)
        
        # Request coordinator refresh
        await self.coordinator.async_request_refresh()