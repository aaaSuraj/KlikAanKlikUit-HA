"""Binary sensor platform for KlikAanKlikUit ICS-2000."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
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
    ATTR_LAST_COMMAND,
    ATTR_LAST_UPDATE,
    ATTR_ZIGBEE,
    DEVICE_TYPE_SENSOR,
    DEVICE_TYPE_DOORBELL,
    DOMAIN,
)
from .hub import ICS2000Hub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KlikAanKlikUit binary sensors."""
    
    data = hass.data[DOMAIN][config_entry.entry_id]
    hub: ICS2000Hub = data["hub"]
    coordinator: DataUpdateCoordinator = data["coordinator"]
    
    # Create binary sensor entities
    entities = []
    for device in hub.get_all_devices():
        if device[ATTR_DEVICE_TYPE] in [DEVICE_TYPE_SENSOR, DEVICE_TYPE_DOORBELL]:
            entities.append(
                KakuBinarySensor(
                    coordinator,
                    hub,
                    device[ATTR_DEVICE_ID],
                    config_entry.entry_id,
                )
            )
            _LOGGER.info(f"Created binary sensor entity for device {device[ATTR_DEVICE_ID]}: {device[ATTR_DEVICE_MODEL]}")
    
    if entities:
        async_add_entities(entities)
        _LOGGER.info(f"Added {len(entities)} binary sensor entities")


class KakuBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """KlikAanKlikUit Binary Sensor."""
    
    _attr_has_entity_name = True
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        hub: ICS2000Hub,
        device_id: int,
        config_entry_id: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        
        self._hub = hub
        self._device_id = device_id
        self._config_entry_id = config_entry_id
        
        # Set unique ID
        self._attr_unique_id = f"{hub.mac}_{device_id}"
        
        # Get device info
        self._device = hub.get_device(device_id) or {}
        
        # Set name based on device model
        device_model = self._device.get(ATTR_DEVICE_MODEL, "Sensor")
        self._attr_name = f"{device_model} {device_id}"
        
        # Determine device class based on model
        model_lower = device_model.lower()
        if "motion" in model_lower:
            self._attr_device_class = BinarySensorDeviceClass.MOTION
        elif "door" in model_lower or "window" in model_lower:
            self._attr_device_class = BinarySensorDeviceClass.DOOR
        elif "doorbell" in model_lower:
            self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY
        else:
            self._attr_device_class = BinarySensorDeviceClass.MOTION
        
        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{hub.mac}_{device_id}")},
            name=self._attr_name,
            manufacturer="KlikAanKlikUit",
            model=self._device.get(ATTR_DEVICE_MODEL, "Unknown"),
            via_device=(DOMAIN, hub.mac),
        )
        
        # For Zigbee sensors, we don't assume state
        if self._device.get(ATTR_ZIGBEE, False):
            self._attr_assumed_state = False
        else:
            self._attr_assumed_state = True
    
    @property
    def is_on(self) -> bool:
        """Return true if sensor is on/triggered."""
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
        }
        
        # Add state tracking info
        if ATTR_LAST_COMMAND in device:
            attributes[ATTR_LAST_COMMAND] = device[ATTR_LAST_COMMAND]
        if ATTR_LAST_UPDATE in device:
            attributes[ATTR_LAST_UPDATE] = device[ATTR_LAST_UPDATE]
        if ATTR_CONFIDENCE in device:
            attributes[ATTR_CONFIDENCE] = f"{device[ATTR_CONFIDENCE]}%"
        
        # Add battery level if available (for Zigbee sensors)
        if device.get("battery_level") is not None:
            attributes["battery_level"] = f"{device['battery_level']}%"
        
        # Add signal strength if available
        if device.get("rssi") is not None:
            attributes["signal_strength"] = device["rssi"]
        
        return attributes
