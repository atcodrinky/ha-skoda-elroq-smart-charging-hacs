"""Skoda Elroq Smart Charging - Home Assistant Integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.components import mqtt

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
    DEFAULT_CONTRACT_POWER_W,
    DEFAULT_BATTERY_CAPACITY_KWH,
    DEFAULT_ALLOWED_IMPORT_W,
    DEFAULT_MIN_CHARGE_CURRENT_A,
    DEFAULT_MAX_CHARGE_CURRENT_A,
    DEFAULT_NIGHT_POWER_LIMIT_W,
    DEFAULT_USER_SOC_TARGET,
    DEFAULT_VEHICLE_SOC_TARGET,
    CHARGING_MODE_IDLE,
    CHARGING_MODE_PV_SURPLUS,
    CHARGING_MODE_NIGHT_F3,
    CHARGING_MODE_FORCE,
    CHARGING_MODE_MASTER_STOP,
    MQTT_MODE_SOLAR,
    MQTT_MODE_NORMAL,
    MQTT_MODE_PAUSE,
)
from .coordinator import SkodaElroqCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER, Platform.SELECT]

SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Skoda Elroq Smart Charging from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = SkodaElroqCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async def handle_authorize_charging(call: ServiceCall) -> None:
        """Handle charging authorization service call."""
        await coordinator.authorize_charging()

    async def handle_revoke_charging(call: ServiceCall) -> None:
        """Handle charging revocation service call."""
        await coordinator.revoke_charging()

    async def handle_set_charge_limit(call: ServiceCall) -> None:
        """Handle setting charge current limit service call."""
        current_a = call.data.get("current_a", DEFAULT_MIN_CHARGE_CURRENT_A)
        await coordinator.set_current_limit(current_a)

    hass.services.async_register(DOMAIN, "authorize_charging", handle_authorize_charging)
    hass.services.async_register(DOMAIN, "revoke_charging", handle_revoke_charging)
    hass.services.async_register(DOMAIN, "set_charge_limit", handle_set_charge_limit)

    # Start background charging loop
    entry.async_on_unload(
        async_track_time_interval(hass, coordinator.async_update_charging_logic, timedelta(seconds=30))
    )

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
