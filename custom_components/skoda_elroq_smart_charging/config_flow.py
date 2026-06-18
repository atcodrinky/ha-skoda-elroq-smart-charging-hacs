"""Config flow for Skoda Elroq Smart Charging."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_MQTT_TOPIC_BASE,
    CONF_CONTRACT_POWER_W,
    CONF_BATTERY_CAPACITY_KWH,
    CONF_VEHICLE_SOC_ENTITY,
    CONF_VEHICLE_CHARGE_LIMIT_ENTITY,
    CONF_VEHICLE_CONNECTED_ENTITY,
    CONF_GRID_POWER_ENTITY,
    CONF_PV_POWER_ENTITY,
    CONF_WALLBOX_POWER_ENTITY,
    CONF_WALLBOX_VOLTAGE_ENTITY,
    CONF_TARIFF_BAND_ENTITY,
    CONF_WALLBOX_STATE_ENTITY,
    DEFAULT_MQTT_TOPIC_BASE,
    DEFAULT_CONTRACT_POWER_W,
    DEFAULT_BATTERY_CAPACITY_KWH,
)

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MQTT_TOPIC_BASE, default=DEFAULT_MQTT_TOPIC_BASE): str,
        vol.Required(CONF_CONTRACT_POWER_W, default=DEFAULT_CONTRACT_POWER_W): vol.Coerce(int),
        vol.Required(CONF_BATTERY_CAPACITY_KWH, default=DEFAULT_BATTERY_CAPACITY_KWH): vol.Coerce(float),
    }
)

STEP_ENTITIES_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_VEHICLE_SOC_ENTITY, default="sensor.elroq_percentuale_batteria"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Required(CONF_VEHICLE_CHARGE_LIMIT_ENTITY, default="number.elroq_limite_di_carica"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="number")
        ),
        vol.Required(CONF_VEHICLE_CONNECTED_ENTITY, default="binary_sensor.elroq_caricabatterie_collegato"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="binary_sensor")
        ),
        vol.Required(CONF_WALLBOX_STATE_ENTITY, default="sensor.silla_prism_stato_wallbox"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Required(CONF_GRID_POWER_ENTITY, default="sensor.rete_power"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Required(CONF_PV_POWER_ENTITY, default="sensor.fotovoltaico_power"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Required(CONF_WALLBOX_POWER_ENTITY, default="sensor.wallbox_potenza"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Required(CONF_WALLBOX_VOLTAGE_ENTITY, default="sensor.wallbox_tensione"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Required(CONF_TARIFF_BAND_ENTITY, default="sensor.pun_fascia_corrente"): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
    }
)


class SkodaElroqConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Skoda Elroq Smart Charging."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._user_input: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - MQTT and power settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._user_input.update(user_input)
            return await self.async_step_entities()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "mqtt_info": "Inserisci il topic base MQTT del wallbox Silla Prism (es. prism/1)"
            },
        )

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle entity selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._user_input.update(user_input)

            # Validate that required entities exist
            for key, entity_id in user_input.items():
                if not self.hass.states.get(entity_id):
                    errors[key] = "entity_not_found"

            if not errors:
                return self.async_create_entry(
                    title="Skoda Elroq Smart Charging",
                    data=self._user_input,
                )

        return self.async_show_form(
            step_id="entities",
            data_schema=STEP_ENTITIES_SCHEMA,
            errors=errors,
            description_placeholders={
                "entities_info": "Seleziona le entità del veicolo, wallbox e sensori energetici"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SkodaElroqOptionsFlow:
        """Create the options flow."""
        return SkodaElroqOptionsFlow(config_entry)


class SkodaElroqOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Skoda Elroq Smart Charging."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CONTRACT_POWER_W,
                        default=self.config_entry.options.get(
                            CONF_CONTRACT_POWER_W,
                            self.config_entry.data.get(CONF_CONTRACT_POWER_W, DEFAULT_CONTRACT_POWER_W),
                        ),
                    ): vol.Coerce(int),
                    vol.Required(
                        CONF_BATTERY_CAPACITY_KWH,
                        default=self.config_entry.options.get(
                            CONF_BATTERY_CAPACITY_KWH,
                            self.config_entry.data.get(CONF_BATTERY_CAPACITY_KWH, DEFAULT_BATTERY_CAPACITY_KWH),
                        ),
                    ): vol.Coerce(float),
                }
            ),
        )
