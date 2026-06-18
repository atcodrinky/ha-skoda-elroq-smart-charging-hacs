"""Number platform for Skoda Elroq Smart Charging."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    DEFAULT_USER_SOC_TARGET,
    DEFAULT_VEHICLE_SOC_TARGET,
    DEFAULT_ALLOWED_IMPORT_W,
    DEFAULT_NIGHT_POWER_LIMIT_W,
    DEFAULT_CONTRACT_POWER_W,
    NUMBER_USER_SOC_TARGET,
    NUMBER_VEHICLE_SOC_TARGET,
    NUMBER_CONTRACT_POWER,
    NUMBER_ALLOWED_IMPORT,
    NUMBER_NIGHT_POWER_LIMIT,
)
from .coordinator import SkodaElroqCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities from config entry."""
    coordinator: SkodaElroqCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            UserSocTargetNumber(coordinator, entry),
            VehicleSocTargetNumber(coordinator, entry),
            ContractPowerNumber(coordinator, entry),
            AllowedImportNumber(coordinator, entry),
            NightPowerLimitNumber(coordinator, entry),
        ]
    )


class SkodaElroqBaseNumber(CoordinatorEntity[SkodaElroqCoordinator], NumberEntity):
    """Base number entity."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX

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


class UserSocTargetNumber(SkodaElroqBaseNumber):
    """User SOC target (for night/manual charging)."""

    _attr_name = "User SOC Target"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 10
    _attr_native_max_value = 100
    _attr_native_step = 5
    _attr_icon = "mdi:battery-charging-50"

    def __init__(self, coordinator: SkodaElroqCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, NUMBER_USER_SOC_TARGET)

    @property
    def native_value(self) -> float:
        return self.coordinator.user_soc_target

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.user_soc_target = value
        self.coordinator.async_update_listeners()


class VehicleSocTargetNumber(SkodaElroqBaseNumber):
    """Vehicle SOC target (for PV surplus and force charging)."""

    _attr_name = "Vehicle SOC Target"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_min_value = 20
    _attr_native_max_value = 100
    _attr_native_step = 5
    _attr_icon = "mdi:battery-charging-100"

    def __init__(self, coordinator: SkodaElroqCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, NUMBER_VEHICLE_SOC_TARGET)

    @property
    def native_value(self) -> float:
        return self.coordinator.vehicle_soc_target

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.vehicle_soc_target = value
        self.coordinator.async_update_listeners()


class ContractPowerNumber(SkodaElroqBaseNumber):
    """Maximum contract power for load balancing."""

    _attr_name = "Contract Power Limit"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_native_min_value = 1500
    _attr_native_max_value = 15000
    _attr_native_step = 100
    _attr_icon = "mdi:transmission-tower"

    def __init__(self, coordinator: SkodaElroqCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, NUMBER_CONTRACT_POWER)

    @property
    def native_value(self) -> float:
        return self.coordinator._contract_power_w

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator._contract_power_w = value
        self.coordinator.async_update_listeners()


class AllowedImportNumber(SkodaElroqBaseNumber):
    """Allowed grid import while in PV surplus charging mode."""

    _attr_name = "Allowed Grid Import"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_native_min_value = 0
    _attr_native_max_value = 2000
    _attr_native_step = 50
    _attr_icon = "mdi:transmission-tower-import"

    def __init__(self, coordinator: SkodaElroqCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, NUMBER_ALLOWED_IMPORT)

    @property
    def native_value(self) -> float:
        return self.coordinator.allowed_import_w

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.allowed_import_w = value
        self.coordinator.async_update_listeners()


class NightPowerLimitNumber(SkodaElroqBaseNumber):
    """Optional night charging power cap."""

    _attr_name = "Night Charging Power Limit"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_native_min_value = 1000
    _attr_native_max_value = 11000
    _attr_native_step = 100
    _attr_icon = "mdi:weather-night"

    def __init__(self, coordinator: SkodaElroqCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, NUMBER_NIGHT_POWER_LIMIT)

    @property
    def native_value(self) -> float:
        return self.coordinator.night_power_limit_w

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.night_power_limit_w = value
        self.coordinator.async_update_listeners()
