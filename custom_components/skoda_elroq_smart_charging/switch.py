"""Switch platform for Skoda Elroq Smart Charging."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SWITCH_MASTER_STOP,
    SWITCH_FORCE_CHARGE,
    SWITCH_SOLAR_CONTROLLER,
)
from .coordinator import SkodaElroqCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities from config entry."""
    coordinator: SkodaElroqCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            MasterStopSwitch(coordinator, entry),
            ForceChargeSwitch(coordinator, entry),
            SolarControllerSwitch(coordinator, entry),
        ]
    )


class SkodaElroqBaseSwitch(CoordinatorEntity[SkodaElroqCoordinator], SwitchEntity):
    """Base switch entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SkodaElroqCoordinator, entry: ConfigEntry, unique_suffix: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Skoda Elroq Smart Charging",
            "manufacturer": "atcodrinky",
            "model": "EV Energy Manager",
        }


class MasterStopSwitch(SkodaElroqBaseSwitch):
    """Master Stop switch – globally blocks all charging."""

    _attr_name = "Master Stop"
    _attr_icon = "mdi:stop-circle"

    def __init__(self, coordinator: SkodaElroqCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, SWITCH_MASTER_STOP)

    @property
    def is_on(self) -> bool:
        return self.coordinator.master_stop

    async def async_turn_on(self, **kwargs: Any) -> None:
        _LOGGER.warning("Master Stop ENABLED – all charging blocked")
        self.coordinator.master_stop = True
        await self.coordinator.async_update_charging_logic()

    async def async_turn_off(self, **kwargs: Any) -> None:
        _LOGGER.info("Master Stop DISABLED")
        self.coordinator.master_stop = False
        self.coordinator.async_update_listeners()


class ForceChargeSwitch(SkodaElroqBaseSwitch):
    """Force Charge switch – charges immediately ignoring tariff/solar."""

    _attr_name = "Force Charge"
    _attr_icon = "mdi:flash"

    def __init__(self, coordinator: SkodaElroqCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, SWITCH_FORCE_CHARGE)

    @property
    def is_on(self) -> bool:
        return self.coordinator.force_charge

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self.coordinator.master_stop:
            _LOGGER.warning("Cannot enable Force Charge: Master Stop is active")
            return
        _LOGGER.info("Force Charge ENABLED")
        self.coordinator.force_charge = True
        await self.coordinator.async_update_charging_logic()

    async def async_turn_off(self, **kwargs: Any) -> None:
        _LOGGER.info("Force Charge DISABLED")
        self.coordinator.force_charge = False
        await self.coordinator.revoke_charging()
        self.coordinator.async_update_listeners()


class SolarControllerSwitch(SkodaElroqBaseSwitch):
    """Solar Controller active switch – read/write indicator."""

    _attr_name = "Solar Controller Active"
    _attr_icon = "mdi:solar-power-variant"

    def __init__(self, coordinator: SkodaElroqCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, SWITCH_SOLAR_CONTROLLER)

    @property
    def is_on(self) -> bool:
        return self.coordinator.solar_controller_active

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.coordinator.solar_controller_active = True
        self.coordinator.async_update_listeners()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.coordinator.solar_controller_active = False
        self.coordinator.async_update_listeners()
