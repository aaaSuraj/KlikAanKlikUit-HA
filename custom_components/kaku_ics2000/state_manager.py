"""State manager for KlikAanKlikUit ICS-2000 devices."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

_LOGGER = logging.getLogger(__name__)


class StateManager:
    """Manages device states for KlikAanKlikUit devices."""
    
    def __init__(self) -> None:
        """Initialize the state manager."""
        self._states: Dict[int, Dict[str, Any]] = {}
        self._last_update: Optional[datetime] = None
    
    def update_device_state(self, device_id: int, state: Dict[str, Any]) -> None:
        """Update the state of a device."""
        self._states[device_id] = state
        self._last_update = datetime.now()
        _LOGGER.debug(f"Updated state for device {device_id}: {state}")
    
    def get_device_state(self, device_id: int) -> Optional[Dict[str, Any]]:
        """Get the state of a device."""
        return self._states.get(device_id)
    
    def get_all_states(self) -> Dict[int, Dict[str, Any]]:
        """Get all device states."""
        return self._states.copy()
    
    def clear_states(self) -> None:
        """Clear all device states."""
        self._states.clear()
        self._last_update = None
        _LOGGER.debug("Cleared all device states")
    
    @property
    def last_update(self) -> Optional[datetime]:
        """Get the last update time."""
        return self._last_update
    
    def is_device_on(self, device_id: int) -> bool:
        """Check if a device is on."""
        state = self._states.get(device_id, {})
        return state.get("state", False)
    
    def get_device_brightness(self, device_id: int) -> Optional[int]:
        """Get the brightness of a device."""
        state = self._states.get(device_id, {})
        return state.get("brightness")
    
    def get_device_position(self, device_id: int) -> Optional[int]:
        """Get the position of a cover device."""
        state = self._states.get(device_id, {})
        return state.get("position")
