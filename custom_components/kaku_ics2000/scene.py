"""Scene platform for KlikAanKlikUit ICS-2000."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .hub import ICS2000Hub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KlikAanKlikUit scenes."""
    
    data = hass.data[DOMAIN][config_entry.entry_id]
    hub: ICS2000Hub = data["hub"]
    
    # Create scene entities
    entities = []
    for scene in hub.get_all_scenes():
        entities.append(
            KakuScene(
                hub,
                scene["entityId"],
                scene["name"],
                config_entry.entry_id,
            )
        )
        _LOGGER.info(f"Created scene entity: {scene['name']} (ID: {scene['entityId']})")
    
    if entities:
        async_add_entities(entities)
        _LOGGER.info(f"Added {len(entities)} scene entities")


class KakuScene(Scene):
    """KlikAanKlikUit Scene."""
    
    _attr_has_entity_name = True
    
    def __init__(
        self,
        hub: ICS2000Hub,
        scene_id: int,
        name: str,
        config_entry_id: str,
    ) -> None:
        """Initialize the scene."""
        self._hub = hub
        self._scene_id = scene_id
        self._config_entry_id = config_entry_id
        
        # Set unique ID
        self._attr_unique_id = f"{hub.mac}_scene_{scene_id}"
        
        # Set name
        self._attr_name = name
        
        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{hub.mac}_scene_{scene_id}")},
            name=name,
            manufacturer="KlikAanKlikUit",
            model="Scene",
            via_device=(DOMAIN, hub.mac),
        )
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._hub.connected
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        scene = self._hub.scenes.get(self._scene_id, {})
        return {
            "scene_id": self._scene_id,
            "devices": scene.get("devices", []),
        }
    
    async def async_activate(self, **kwargs: Any) -> None:
        """Activate the scene."""
        await self._hub.async_run_scene(self._scene_id)
        _LOGGER.info(f"Activated scene: {self._attr_name}")
