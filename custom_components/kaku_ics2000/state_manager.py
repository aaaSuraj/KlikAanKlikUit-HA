"""State manager for KlikAanKlikUit ICS-2000."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_CONFIDENCE,
    ATTR_LAST_UPDATE,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_UNCERTAIN,
)

_LOGGER = logging.getLogger(__name__)


class StateManager:
    """Manage device states with persistence."""
    
    def __init__(self, hass: HomeAssistant, store: Store) -> None:
        """Initialize state manager."""
        self.hass = hass
        self._store = store
        self._states: Dict[int, Dict[str, Any]] = {}
        self._loaded = False
    
    async def async_load(self) -> None:
        """Load states from storage."""
        if self._loaded:
            return
        
        try:
            data = await self._store.async_load()
            if data:
                self._states = {
                    int(k): v for k, v in data.get("states", {}).items()
                }
                _LOGGER.info(f"Loaded {len(self._states)} device states")
            else:
                self._states = {}
        except Exception as err:
            _LOGGER.error(f"Failed to load states: {err}")
            self._states = {}
        
        self._loaded = True
    
    async def async_save(self) -> None:
        """Save states to storage."""
        try:
            await self._store.async_save({
                "states": {str(k): v for k, v in self._states.items()},
                "last_save": datetime.now().isoformat(),
            })
            _LOGGER.debug(f"Saved {len(self._states)} device states")
        except Exception as err:
            _LOGGER.error(f"Failed to save states: {err}")
    
    async def async_get_device_state(
        self,
        device_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Get saved state for a device."""
        if not self._loaded:
            await self.async_load()
        
        state = self._states.get(device_id)
        if state:
            # Update confidence based on age
            state = self._update_confidence(state)
        
        return state
    
    async def async_update_device_state(
        self,
        device_id: int,
        state: Dict[str, Any],
    ) -> None:
        """Update and save device state."""
        if not self._loaded:
            await self.async_load()
        
        # Store state
        self._states[device_id] = state.copy()
        
        # Save periodically (not on every update for performance)
        if len(self._states) % 10 == 0:  # Save every 10 updates
            await self.async_save()
    
    async def async_reset_device_state(self, device_id: int) -> None:
        """Reset state for a specific device."""
        if device_id in self._states:
            del self._states[device_id]
            await self.async_save()
            _LOGGER.info(f"Reset state for device {device_id}")
    
    async def async_reset_all_states(self) -> None:
        """Reset all device states."""
        self._states = {}
        await self.async_save()
        _LOGGER.info("Reset all device states")
    
    def _update_confidence(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Update confidence level based on state age."""
        last_update = state.get(ATTR_LAST_UPDATE)
        if not last_update:
            state[ATTR_CONFIDENCE] = CONFIDENCE_UNCERTAIN
            return state
        
        try:
            # Parse last update time
            if isinstance(last_update, str):
                last_time = datetime.fromisoformat(last_update)
            else:
                last_time = last_update
            
            # Calculate age
            age = datetime.now() - last_time
            
            # Set confidence based on age
            if age < timedelta(minutes=1):
                state[ATTR_CONFIDENCE] = CONFIDENCE_HIGH
            elif age < timedelta(minutes=5):
                state[ATTR_CONFIDENCE] = CONFIDENCE_MEDIUM
            elif age < timedelta(hours=1):
                state[ATTR_CONFIDENCE] = CONFIDENCE_LOW
            else:
                state[ATTR_CONFIDENCE] = CONFIDENCE_UNCERTAIN
        
        except Exception as err:
            _LOGGER.debug(f"Failed to update confidence: {err}")
            state[ATTR_CONFIDENCE] = CONFIDENCE_UNCERTAIN
        
        return state
    
    async def async_get_all_states(self) -> Dict[int, Dict[str, Any]]:
        """Get all device states."""
        if not self._loaded:
            await self.async_load()
        
        # Update confidence for all states
        return {
            device_id: self._update_confidence(state)
            for device_id, state in self._states.items()
        }
    
    async def async_cleanup_old_states(self, days: int = 30) -> None:
        """Remove states older than specified days."""
        if not self._loaded:
            await self.async_load()
        
        cutoff = datetime.now() - timedelta(days=days)
        removed = 0
        
        for device_id in list(self._states.keys()):
            state = self._states[device_id]
            last_update = state.get(ATTR_LAST_UPDATE)
            
            if last_update:
                try:
                    if isinstance(last_update, str):
                        last_time = datetime.fromisoformat(last_update)
                    else:
                        last_time = last_update
                    
                    if last_time < cutoff:
                        del self._states[device_id]
                        removed += 1
                except Exception:
                    pass
        
        if removed > 0:
            await self.async_save()
            _LOGGER.info(f"Cleaned up {removed} old device states")
