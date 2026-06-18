"""Sensor platform for Skoda Elroq Smart Charging."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower, UnitOfElectricCurrent, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SENSOR_CHARGING_MODE,
    SENSOR_PV_SURPLUS,
    SENSOR_TARGET_SOC,
    SENSOR_TIME_REMAINING,
    SENSOR_CHARGE_END_TIME,
    SENSOR_WALLBOX_CURRENT_TARGET,
    CHARGING_MODE_IDLE,
    CHARGING_MODE_PV_SURPLUS,
    CHARGING_MODE_NIGHT_F3,
    CHARGING_MODE_FORCE,
    CHARGING_MODE_MASTER_STOP,
)
from .coordinator import SkodaElroqCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from config entry."""
    coordinator: SkodaElroqCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            ChargingModeSensor(coordinator, entry),
            PvSurplusSensor(coordinator, entry),
            TargetSocSensor(coordinator, entry),
            TimeRemainingSensor(coordinator, entry),
            ChargeEndTimeSensor(coordinator, entry),
            WallboxCurrentTargetSensor(coordinator, entry),
        ]
    )


class SkodaElroqBaseSensor(CoordinatorEntity[SkodaElroqCoordinator], SensorEntity):
    """Base sensor entity for Skoda Elroq Smart Charging."""

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

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success


class ChargingModeSensor(SkodaElroqBaseSensor):
    """Current charging mode sensor."""

    _attr_name = "Charging Mode"
    _attr_icon = "mdi:ev-station"

    def __init__(self, coordinator: SkodaElroqCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, SENSOR_CHARGING_MODE)

    @property
    def native_value(self) -> str:
        return self.coordinator.charging_mode

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "vehicle_soc": data.get("vehicle_soc"),
            "vehicle_connected": data.get("vehicle_connected"),
            "tariff_band": data.get("tariff_band"),
            "master_stop": self.coordinator.master_stop,
            "force_charge": self.coordinator.force_charge,
            "solar_controller_active": self.coordinator.solar_controller_active,
        }


class PvSurplusSensor(SkodaElroqBaseSensor):
    """PV surplus power sensor."""

    _attr_name = "PV Surplus"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:solar-power"

    def __init__(self, coordinator: SkodaElroqCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, SENSOR_PV_SURPLUS)

    @property
    def native_value(self) -> float:
        return round(self.coordinator.pv_surplus_w, 1)


class TargetSocSensor(SkodaElroqBaseSensor):
    """Active SOC target sensor."""

    _attr_name = "Target SOC"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:battery-charging-100"

    def __init__(self, coordinator: SkodaElroqCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, SENSOR_TARGET_SOC)

    @property
    def native_value(self) -> float:
        data = self.coordinator.data or {}
        return data.get("target_soc_active", self.coordinator.vehicle_soc_target)


class TimeRemainingSensor(SkodaElroqBaseSensor):
    """Estimated charging time remaining sensor."""

    _attr_name = "Charging Time Remaining"
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator: SkodaElroqCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, SENSOR_TIME_REMAINING)

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data or {}
        minutes = data.get("remaining_minutes")
        if minutes is None:
            return None
        h = int(minutes // 60)
        m = int(minutes % 60)
        if h > 0:
            return f"{h}h {m:02d}m"
        return f"{m}m"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {"remaining_minutes": data.get("remaining_minutes")}


class ChargeEndTimeSensor(SkodaElroqBaseSensor):
    """Estimated charge completion timestamp sensor."""

    _attr_name = "Charge End Time"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-end"

    def __init__(self, coordinator: SkodaElroqCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, SENSOR_CHARGE_END_TIME)

    @property
    def native_value(self) -> datetime | None:
        data = self.coordinator.data or {}
        return data.get("charge_end_time")


class WallboxCurrentTargetSensor(SkodaElroqBaseSensor):
    """Theoretical wallbox current target from PV surplus."""

    _attr_name = "Wallbox Current Target"
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:current-ac"

    def __init__(self, coordinator: SkodaElroqCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, SENSOR_WALLBOX_CURRENT_TARGET)

    @property
    def native_value(self) -> float:
        data = self.coordinator.data or {}
        return round(data.get("wallbox_current_target_a", 0.0), 1)
