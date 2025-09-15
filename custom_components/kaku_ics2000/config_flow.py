"""Config flow for KlikAanKlikUit ICS-2000 integration - Homebridge Compatible."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_EMAIL,
    CONF_IP_ADDRESS,
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .const import (
    CONF_AES_KEY,
    CONF_CUSTOM_DISCOVER_MESSAGE,
    CONF_DEVICE_DISCOVERY,
    CONF_ENTITY_BLACKLIST,
    CONF_MQTT_ENABLE,
    CONF_MQTT_TOPIC,
    CONF_REST_SERVER_PORT,
    CONF_SHOW_SCENES,
    CONF_SLEEP,
    CONF_START_REST_SERVER,
    CONF_STATE_RESTORE,
    CONF_TRIES,
    DEFAULT_DEVICE_DISCOVERY,
    DEFAULT_MQTT_ENABLE,
    DEFAULT_MQTT_TOPIC,
    DEFAULT_REST_SERVER_PORT,
    DEFAULT_SHOW_SCENES,
    DEFAULT_SLEEP,
    DEFAULT_STATE_RESTORE,
    DEFAULT_TRIES,
    DOMAIN,
)
from .hub import ICS2000Hub

_LOGGER = logging.getLogger(__name__)


async def validate_mac(mac: str) -> str:
    """Validate and format MAC address."""
    # Remove any separators and convert to uppercase
    mac = mac.upper().replace(":", "").replace("-", "").replace(" ", "")
    
    # Check if valid hex and correct length
    if len(mac) != 12 or not all(c in "0123456789ABCDEF" for c in mac):
        raise InvalidMAC("Invalid MAC address format")
    
    # Format with colons
    return ":".join(mac[i:i+2] for i in range(0, 12, 2))


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    
    # Validate MAC address
    mac = await validate_mac(data[CONF_MAC])
    data[CONF_MAC] = mac
    
    # Create hub instance for testing (Homebridge style)
    hub = ICS2000Hub(
        hass=hass,
        mac=mac,
        email=data[CONF_EMAIL],
        password=data[CONF_PASSWORD],
        ip_address=data.get(CONF_IP_ADDRESS),
        aes_key=data.get(CONF_AES_KEY),
    )
    
    # Test connection with Homebridge-style authentication
    try:
        await hub.async_connect()
        devices = await hub.async_discover_devices()
        device_count = len(devices)
        scene_count = len(hub.scenes)
    except asyncio.TimeoutError:
        raise CannotConnect("Connection timeout")
    except Exception as err:
        error_str = str(err).lower()
        if "auth" in error_str or "password" in error_str or "pass" in error_str:
            raise InvalidAuth("Invalid credentials - check email and password")
        raise CannotConnect(f"Failed to connect: {err}")
    finally:
        await hub.async_disconnect()
    
    # Return info for the entry
    return {
        "title": data.get(CONF_NAME, f"ICS-2000 ({mac[-8:]})"),
        "device_count": device_count,
        "scene_count": scene_count,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for KlikAanKlikUit ICS-2000 - Homebridge Compatible."""
    
    VERSION = 1
    
    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: dict[str, Any] = {}
        self._discovered_mac: str | None = None
    
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                
                # Set unique ID
                await self.async_set_unique_id(user_input[CONF_MAC])
                self._abort_if_unique_id_configured()
                
                # Create entry with Homebridge-compatible defaults
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                    options={
                        CONF_TRIES: DEFAULT_TRIES,
                        CONF_SLEEP: DEFAULT_SLEEP,
                        CONF_STATE_RESTORE: DEFAULT_STATE_RESTORE,
                        CONF_DEVICE_DISCOVERY: DEFAULT_DEVICE_DISCOVERY,
                        CONF_MQTT_ENABLE: DEFAULT_MQTT_ENABLE,
                        CONF_MQTT_TOPIC: DEFAULT_MQTT_TOPIC,
                        CONF_SHOW_SCENES: DEFAULT_SHOW_SCENES,
                        CONF_ENTITY_BLACKLIST: [],
                        CONF_START_REST_SERVER: False,
                        CONF_REST_SERVER_PORT: DEFAULT_REST_SERVER_PORT,
                    },
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except InvalidMAC:
                errors[CONF_MAC] = "invalid_mac"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
        
        # Show form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MAC): str,
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_IP_ADDRESS): str,
                    vol.Optional(CONF_AES_KEY): str,
                    vol.Optional(CONF_NAME): str,
                }
            ),
            errors=errors,
        )
    
    async def async_step_discovery(
        self, discovery_info: dict[str, Any]
    ) -> FlowResult:
        """Handle discovery."""
        # Store discovery info
        self._discovery_info = discovery_info
        self._discovered_mac = discovery_info.get("mac")
        
        if self._discovered_mac:
            await self.async_set_unique_id(self._discovered_mac)
            self._abort_if_unique_id_configured()
        
        # Ask user for credentials
        return await self.async_step_discovery_confirm()
    
    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # Combine with discovery info
            full_input = {
                CONF_MAC: self._discovered_mac,
                CONF_IP_ADDRESS: self._discovery_info.get("ip"),
                **user_input,
            }
            
            try:
                info = await validate_input(self.hass, full_input)
                
                return self.async_create_entry(
                    title=info["title"],
                    data=full_input,
                    options={
                        CONF_TRIES: DEFAULT_TRIES,
                        CONF_SLEEP: DEFAULT_SLEEP,
                        CONF_STATE_RESTORE: DEFAULT_STATE_RESTORE,
                        CONF_DEVICE_DISCOVERY: DEFAULT_DEVICE_DISCOVERY,
                        CONF_MQTT_ENABLE: DEFAULT_MQTT_ENABLE,
                        CONF_MQTT_TOPIC: DEFAULT_MQTT_TOPIC,
                        CONF_SHOW_SCENES: DEFAULT_SHOW_SCENES,
                        CONF_ENTITY_BLACKLIST: [],
                        CONF_START_REST_SERVER: False,
                        CONF_REST_SERVER_PORT: DEFAULT_REST_SERVER_PORT,
                    },
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
        
        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={
                "mac": self._discovered_mac,
                "ip": self._discovery_info.get("ip", "Unknown"),
            },
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_NAME): str,
                }
            ),
            errors=errors,
        )
    
    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlow:
        """Get options flow."""
        return OptionsFlow(config_entry)


class OptionsFlow(config_entries.OptionsFlow):
    """Handle options flow - Homebridge Compatible."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__(config_entry)
    
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        
        # Check if MQTT is available
        mqtt_available = False
        try:
            mqtt_available = "mqtt" in self.hass.config.components
        except Exception:
            mqtt_available = False
        
        schema_dict = {
            vol.Optional(
                CONF_TRIES,
                default=self.config_entry.options.get(CONF_TRIES, DEFAULT_TRIES),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=10,
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Optional(
                CONF_SLEEP,
                default=self.config_entry.options.get(CONF_SLEEP, DEFAULT_SLEEP),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=10,
                    mode=selector.NumberSelectorMode.SLIDER,
                    unit_of_measurement="seconds",
                )
            ),
            vol.Optional(
                CONF_STATE_RESTORE,
                default=self.config_entry.options.get(
                    CONF_STATE_RESTORE, DEFAULT_STATE_RESTORE
                ),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_DEVICE_DISCOVERY,
                default=self.config_entry.options.get(
                    CONF_DEVICE_DISCOVERY, DEFAULT_DEVICE_DISCOVERY
                ),
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_SHOW_SCENES,
                default=self.config_entry.options.get(
                    CONF_SHOW_SCENES, DEFAULT_SHOW_SCENES
                ),
                description="Show scenes from ICS-2000 (Homebridge feature)",
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_ENTITY_BLACKLIST,
                default=self.config_entry.options.get(CONF_ENTITY_BLACKLIST, []),
                description="Entity IDs to exclude (comma-separated)",
            ): selector.TextSelector(
                selector.TextSelectorConfig(
                    multiline=False,
                )
            ),
            vol.Optional(
                CONF_CUSTOM_DISCOVER_MESSAGE,
                default=self.config_entry.options.get(CONF_CUSTOM_DISCOVER_MESSAGE, ""),
                description="Custom discovery message (Homebridge feature)",
            ): selector.TextSelector(),
        }
        
        # Add MQTT options if available
        if mqtt_available:
            schema_dict.update({
                vol.Optional(
                    CONF_MQTT_ENABLE,
                    default=self.config_entry.options.get(
                        CONF_MQTT_ENABLE, DEFAULT_MQTT_ENABLE
                    ),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_MQTT_TOPIC,
                    default=self.config_entry.options.get(
                        CONF_MQTT_TOPIC, DEFAULT_MQTT_TOPIC
                    ),
                ): selector.TextSelector(),
            })
        
        # Add REST server options (Homebridge feature)
        schema_dict.update({
            vol.Optional(
                CONF_START_REST_SERVER,
                default=self.config_entry.options.get(CONF_START_REST_SERVER, False),
                description="Start REST API server (Homebridge feature)",
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_REST_SERVER_PORT,
                default=self.config_entry.options.get(
                    CONF_REST_SERVER_PORT, DEFAULT_REST_SERVER_PORT
                ),
                description="REST server port",
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1024,
                    max=65535,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        })
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidMAC(HomeAssistantError):
    """Error to indicate invalid MAC address."""
