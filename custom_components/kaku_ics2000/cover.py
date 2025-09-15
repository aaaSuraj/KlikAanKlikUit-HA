"""Cover platform for KlikAanKlikUit ICS-2000."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverEntity,
    CoverEntityFeature,
    CoverDeviceClass,
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
    DEVICE_TYPE_COVER,
    DOMAIN,
)
from .hub import ICS2000Hub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KlikAanKlikUit covers."""
    
    data = hass.data[DOMAIN][config_entry.entry_id]
    hub: ICS2000Hub = data["hub"]
    coordinator: DataUpdateCoordinator = data["coordinator"]
    
    # Create cover entities
    entities = []
    for device in hub.get_all_devices():
        if device[ATTR_DEVICE_TYPE] == DEVICE_TYPE_COVER:
            entities.append(
                KakuCover(
                    coordinator,
                    hub,
                    device[ATTR_DEVICE_ID],
                    config_entry.entry_id,
                )
            )
            _LOGGER.info(f"Created cover entity for device {device[ATTR_DEVICE_ID]}: {device[ATTR_DEVICE_MODEL]}")
    
    if entities:
        async_add_entities(entities)
        _LOGGER.info(f"Added {len(entities)} cover entities")


class KakuCover(CoordinatorEntity, CoverEntity):
    """KlikAanKlikUit Cover."""
    
    _attr_has_entity_name = True
    _attr_assumed_state = True  # Important: This is a one-way device
    
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        hub: ICS2000Hub,
        device_id: int,
        config_entry_id: str,
    ) -> None:
        """Initialize the cover."""
        super().__init__(coordinator)
        
        self._hub = hub
        self._device_id = device_id
        self._config_entry_id = config_entry_id
        
        # Set unique ID
        self._attr_unique_id = f"{hub.mac}_{device_id}"
        
        # Get device info
        self._device = hub.get_device(device_id) or {}
        
        # Set name based on device model
        device_model = self._device.get(ATTR_DEVICE_MODEL, "Cover")
        self._attr_name = f"{device_model} {device_id}"
        
        # Determine device class based on model
        model_lower = device_model.lower()
        if "blind" in model_lower or "roller" in model_lower:
            self._attr_device_class = CoverDeviceClass.BLIND
        elif "shutter" in model_lower:
            self._attr_device_class = CoverDeviceClass.SHUTTER
        elif "curtain" in model_lower:
            self._attr_device_class = CoverDeviceClass.CURTAIN
        else:
            self._attr_device_class = CoverDeviceClass.BLIND
        
        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{hub.mac}_{device_id}")},
            name=self._attr_name,
            manufacturer="KlikAanKlikUit",
            model=self._device.get(ATTR_DEVICE_MODEL, "Unknown"),
            via_device=(DOMAIN, hub.mac),
        )
        
        # Set supported features
        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.SET_POSITION
            | CoverEntityFeature.STOP
        )
    
    @property
    def is_closed(self) -> bool | None:
        """Return true if cover is closed."""
        device = self._hub.get_device(self._device_id)
        if not device:
            return None
        
        position = device.get("position")
        if position is not None:
            return position == 0
        
        # Fall back to state
        state = device.get("state", False)
        return not state  # If state is False, cover is closed
    
    @property
    def is_opening(self) -> bool:
        """Return true if cover is opening."""
        return False  # We can't know this for one-way devices
    
    @property
    def is_closing(self) -> bool:
        """Return true if cover is closing."""
        return False  # We can't know this for one-way devices
    
    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover (0-100)."""
        device = self._hub.get_device(self._device_id)
        if device:
            position = device.get("position")
            if position is not None:
                return position
            
            # Fall back to state-based position
            state = device.get("state", False)
            return 100 if state else 0
        
        return None
    
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
        
        return attributes
    
    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        await self._hub.async_turn_on(self._device_id)
        await self._hub._update_device_state(self._device_id, {"position": 100})
        
        # Request coordinator refresh
        await self.coordinator.async_request_refresh()
    
    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        await self._hub.async_turn_off(self._device_id)
        await self._hub._update_device_state(self._device_id, {"position": 0})
        
        # Request coordinator refresh
        await self.coordinator.async_request_refresh()
    
    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        # For one-way devices, we can't really stop them
        # But we can update the assumed position to 50%
        await self._hub._update_device_state(self._device_id, {"position": 50})
        
        # Request coordinator refresh
        await self.coordinator.async_request_refresh()
    
    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Set the cover position."""
        position = kwargs.get(ATTR_POSITION, 50)
        await self._hub.async_set_cover_position(self._device_id, position)
        
        # Request coordinator refresh
        await self.coordinator.async_request_refresh()
