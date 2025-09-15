"""Sensor platform for KlikAanKlikUit ICS-2000."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    ATTR_CONFIDENCE,
    DEVICE_TYPE_LIGHT,
    DEVICE_TYPE_DIMMER,
    DEVICE_TYPE_SWITCH,
    DEVICE_TYPE_COVER,
    DEVICE_TYPE_SENSOR,
    DOMAIN,
)
from .hub import ICS2000Hub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KlikAanKlikUit sensors."""
    
    data = hass.data[DOMAIN][config_entry.entry_id]
    hub: ICS2000Hub = data["hub"]
    coordinator: DataUpdateCoordinator = data["coordinator"]
    
    # Create hub-level diagnostic sensors
    entities = [
        HubConfidenceSensor(coordinator, hub, config_entry.entry_id),
        HubDeviceCountSensor(coordinator, hub, config_entry.entry_id),
        HubConnectionSensor(coordinator, hub, config_entry.entry_id),
    ]
    
    async_add_entities(entities)
    _LOGGER.info(f"Added {len(entities)} sensor entities")


class HubConfidenceSensor(CoordinatorEntity, SensorEntity):
    """Overall state confidence sensor."""
    
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.POWER_FACTOR
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:gauge"
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        hub: ICS2000Hub,
        config_entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._hub = hub
        self._attr_unique_id = f"{hub.mac}_confidence"
        self._attr_name = "State Confidence"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub.mac)},
        )
    
    @property
    def native_value(self) -> float:
        """Return average confidence."""
        devices = self._hub.get_all_devices()
        if not devices:
            return 0
        
        confidences = [
            d.get(ATTR_CONFIDENCE, 0)
            for d in devices
            if ATTR_CONFIDENCE in d
        ]
        
        return round(sum(confidences) / len(confidences)) if confidences else 0
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        devices = self._hub.get_all_devices()
        
        high = sum(1 for d in devices if d.get(ATTR_CONFIDENCE, 0) >= 80)
        medium = sum(1 for d in devices if 40 <= d.get(ATTR_CONFIDENCE, 0) < 80)
        low = sum(1 for d in devices if d.get(ATTR_CONFIDENCE, 0) < 40)
        
        return {
            "high_confidence": high,
            "medium_confidence": medium,
            "low_confidence": low,
            "high_percentage": round((high / len(devices) * 100) if devices else 0),
            "medium_percentage": round((medium / len(devices) * 100) if devices else 0),
            "low_percentage": round((low / len(devices) * 100) if devices else 0),
        }


class HubDeviceCountSensor(CoordinatorEntity, SensorEntity):
    """Device count sensor."""
    
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:devices"
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        hub: ICS2000Hub,
        config_entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._hub = hub
        self._attr_unique_id = f"{hub.mac}_device_count"
        self._attr_name = "Device Count"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub.mac)},
        )
    
    @property
    def native_value(self) -> int:
        """Return device count."""
        return len(self._hub.get_all_devices())
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        devices = self._hub.get_all_devices()
        
        type_counts = {}
        for device in devices:
            device_type = device.get("device_type", "unknown")
            type_counts[device_type] = type_counts.get(device_type, 0) + 1
        
        # Add friendly names for counts
        friendly_counts = {
            "lights": type_counts.get(DEVICE_TYPE_LIGHT, 0) + type_counts.get(DEVICE_TYPE_DIMMER, 0),
            "switches": type_counts.get(DEVICE_TYPE_SWITCH, 0),
            "covers": type_counts.get(DEVICE_TYPE_COVER, 0),
            "sensors": type_counts.get(DEVICE_TYPE_SENSOR, 0),
        }
        
        # Count Zigbee vs 433MHz devices
        zigbee_count = sum(1 for d in devices if d.get("zigbee", False))
        rf433_count = len(devices) - zigbee_count
        
        return {
            "connected": self._hub.connected,
            "firmware": self._hub.firmware_version,
            "zigbee_devices": zigbee_count,
            "rf433_devices": rf433_count,
            **friendly_counts,
            "raw_types": type_counts,
        }


class HubConnectionSensor(CoordinatorEntity, SensorEntity):
    """Hub connection status sensor."""
    
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:connection"
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        hub: ICS2000Hub,
        config_entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._hub = hub
        self._attr_unique_id = f"{hub.mac}_connection"
        self._attr_name = "Connection Status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub.mac)},
        )
    
    @property
    def native_value(self) -> str:
        """Return connection status."""
        if not self._hub.connected:
            return "Disconnected"
        
        # Check if we have auth token (cloud) or IP (local)
        if hasattr(self._hub, '_auth_token') and self._hub._auth_token:
            return "Connected (Cloud)"
        elif self._hub.ip_address:
            return "Connected (Local)"
        else:
            return "Connected (Fallback Mode)"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        attributes = {
            "connected": self._hub.connected,
            "ip_address": self._hub.ip_address or "Unknown",
            "mac_address": self._hub.mac,
            "firmware": self._hub.firmware_version,
            "retry_attempts": self._hub.tries,
            "retry_delay": self._hub.sleep,
        }
        
        # Add cloud status if available
        if hasattr(self._hub, '_auth_token'):
            attributes["cloud_authenticated"] = bool(self._hub._auth_token)
        
        return attributes
