"""Coordinator for Skoda Elroq Smart Charging - core logic."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

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
    DEFAULT_CONTRACT_POWER_W,
    DEFAULT_BATTERY_CAPACITY_KWH,
    DEFAULT_ALLOWED_IMPORT_W,
    DEFAULT_MIN_CHARGE_CURRENT_A,
    DEFAULT_MAX_CHARGE_CURRENT_A,
    DEFAULT_NIGHT_POWER_LIMIT_W,
    DEFAULT_USER_SOC_TARGET,
    DEFAULT_VEHICLE_SOC_TARGET,
    DEFAULT_SAFETY_MARGIN_W,
    CHARGING_MODE_IDLE,
    CHARGING_MODE_PV_SURPLUS,
    CHARGING_MODE_NIGHT_F3,
    CHARGING_MODE_FORCE,
    CHARGING_MODE_MASTER_STOP,
    MQTT_MODE_SOLAR,
    MQTT_MODE_NORMAL,
    MQTT_MODE_PAUSE,
    TARIFF_F3,
)

_LOGGER = logging.getLogger(__name__)


class SkodaElroqCoordinator(DataUpdateCoordinator):
    """Manages all smart charging logic for Skoda Elroq + Silla Prism."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.entry = entry
        self.hass = hass

        # Configuration from entry
        self._mqtt_base = entry.data.get(CONF_MQTT_TOPIC_BASE, "prism/1")
        self._contract_power_w: float = entry.data.get(CONF_CONTRACT_POWER_W, DEFAULT_CONTRACT_POWER_W)
        self._battery_capacity_kwh: float = entry.data.get(CONF_BATTERY_CAPACITY_KWH, DEFAULT_BATTERY_CAPACITY_KWH)

        # Entity IDs from config
        self._soc_entity = entry.data.get(CONF_VEHICLE_SOC_ENTITY, "sensor.elroq_percentuale_batteria")
        self._charge_limit_entity = entry.data.get(CONF_VEHICLE_CHARGE_LIMIT_ENTITY, "number.elroq_limite_di_carica")
        self._connected_entity = entry.data.get(CONF_VEHICLE_CONNECTED_ENTITY, "binary_sensor.elroq_caricabatterie_collegato")
        self._grid_entity = entry.data.get(CONF_GRID_POWER_ENTITY, "sensor.rete_power")
        self._pv_entity = entry.data.get(CONF_PV_POWER_ENTITY, "sensor.fotovoltaico_power")
        self._wallbox_power_entity = entry.data.get(CONF_WALLBOX_POWER_ENTITY, "sensor.wallbox_potenza")
        self._wallbox_voltage_entity = entry.data.get(CONF_WALLBOX_VOLTAGE_ENTITY, "sensor.wallbox_tensione")
        self._tariff_entity = entry.data.get(CONF_TARIFF_BAND_ENTITY, "sensor.pun_fascia_corrente")
        self._wallbox_state_entity = entry.data.get(CONF_WALLBOX_STATE_ENTITY, "sensor.silla_prism_stato_wallbox")

        # Controllable state (stored in coordinator, exposed via HA entities)
        self.master_stop: bool = False
        self.force_charge: bool = False
        self.solar_controller_active: bool = False
        self.user_soc_target: float = DEFAULT_USER_SOC_TARGET
        self.vehicle_soc_target: float = DEFAULT_VEHICLE_SOC_TARGET
        self.allowed_import_w: float = DEFAULT_ALLOWED_IMPORT_W
        self.night_power_limit_w: float = DEFAULT_NIGHT_POWER_LIMIT_W
        self.last_limit_sent_a: float = 0
        self.last_authorization_ts: datetime | None = None
        self.last_revoke_ts: datetime | None = None

        # Computed / derived state
        self.charging_mode: str = CHARGING_MODE_IDLE
        self.pv_surplus_w: float = 0.0
        self.target_soc_active: float = DEFAULT_VEHICLE_SOC_TARGET
        self.wallbox_current_target_a: float = 0.0

    # ------------------------------------------------------------------
    # DataUpdateCoordinator refresh
    # ------------------------------------------------------------------
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch and compute all derived values."""
        data: dict[str, Any] = {}
        try:
            data["vehicle_soc"] = self._get_float(self._soc_entity)
            data["vehicle_connected"] = self._get_bool(self._connected_entity)
            data["grid_power_w"] = self._get_float(self._grid_entity)
            data["pv_power_w"] = self._get_float(self._pv_entity)
            data["wallbox_power_w"] = self._get_float(self._wallbox_power_entity)
            data["wallbox_voltage_v"] = self._get_float(self._wallbox_voltage_entity, default=230.0)
            data["tariff_band"] = self._get_state(self._tariff_entity, default="F1")
            data["wallbox_state"] = self._get_state(self._wallbox_state_entity, default="unknown")

            # Compute PV surplus: negative grid = export
            grid_w = data["grid_power_w"]
            pv_w = data["pv_power_w"]
            # Surplus = power being exported (negative grid import) plus allowed import
            if grid_w < 0:
                self.pv_surplus_w = abs(grid_w)
            else:
                self.pv_surplus_w = max(0.0, pv_w - grid_w)
            data["pv_surplus_w"] = self.pv_surplus_w

            # Active SOC target
            if self.force_charge or self.solar_controller_active:
                self.target_soc_active = self.vehicle_soc_target
            else:
                self.target_soc_active = self.user_soc_target
            data["target_soc_active"] = self.target_soc_active

            # Charging time estimate
            soc = data["vehicle_soc"]
            remaining_kwh = max(0.0, (self.target_soc_active - soc) / 100.0 * self._battery_capacity_kwh)
            wallbox_kw = data["wallbox_power_w"] / 1000.0
            if wallbox_kw > 0.1:
                remaining_minutes = (remaining_kwh / wallbox_kw) * 60
            else:
                remaining_minutes = None
            data["remaining_minutes"] = remaining_minutes
            if remaining_minutes is not None:
                data["charge_end_time"] = datetime.now() + timedelta(minutes=remaining_minutes)
            else:
                data["charge_end_time"] = None

            # Wallbox theoretical current from surplus
            voltage = data["wallbox_voltage_v"]
            available_w = self.pv_surplus_w + self.allowed_import_w
            self.wallbox_current_target_a = min(
                DEFAULT_MAX_CHARGE_CURRENT_A,
                max(0.0, available_w / voltage)
            )
            data["wallbox_current_target_a"] = self.wallbox_current_target_a

            data["charging_mode"] = self.charging_mode
            data["master_stop"] = self.master_stop
            data["force_charge"] = self.force_charge
            data["solar_controller_active"] = self.solar_controller_active

        except Exception as err:
            raise UpdateFailed(f"Error updating coordinator data: {err}") from err

        return data

    # ------------------------------------------------------------------
    # Main charging decision logic (runs every 30 seconds)
    # ------------------------------------------------------------------
    async def async_update_charging_logic(self, _now: datetime | None = None) -> None:
        """Evaluate charging conditions and act accordingly."""
        await self.async_refresh()
        data = self.data
        if not data:
            return

        vehicle_connected = data.get("vehicle_connected", False)
        vehicle_soc = data.get("vehicle_soc", 0.0)
        tariff_band = data.get("tariff_band", "F1")

        # ── 1. MASTER STOP – highest priority
        if self.master_stop:
            if self.charging_mode != CHARGING_MODE_MASTER_STOP:
                _LOGGER.info("Master Stop active – revoking charging authorization")
                await self.revoke_charging()
                self.charging_mode = CHARGING_MODE_MASTER_STOP
                self.async_update_listeners()
            return

        if not vehicle_connected:
            if self.charging_mode != CHARGING_MODE_IDLE:
                self.charging_mode = CHARGING_MODE_IDLE
                self.solar_controller_active = False
                self.async_update_listeners()
            return

        # ── 2. FORCE CHARGE – override all conditions
        if self.force_charge:
            if vehicle_soc >= self.vehicle_soc_target:
                _LOGGER.info("Force charge complete at SOC %.0f%% – stopping", vehicle_soc)
                self.force_charge = False
                await self.revoke_charging()
                self.charging_mode = CHARGING_MODE_IDLE
            else:
                if self.charging_mode != CHARGING_MODE_FORCE:
                    _LOGGER.info("Force charge activated – authorizing normal charging")
                    await self._set_wallbox_mode(MQTT_MODE_NORMAL)
                    max_a = await self._compute_load_balanced_current()
                    await self.set_current_limit(max_a)
                    await self.authorize_charging()
                    self.charging_mode = CHARGING_MODE_FORCE
                else:
                    # Ongoing force – maintain load balancing
                    max_a = await self._compute_load_balanced_current()
                    await self._send_limit_if_changed(max_a)
            self.async_update_listeners()
            return

        # ── 3. NIGHT F3 TARIFF CHARGING
        if tariff_band == TARIFF_F3:
            if vehicle_soc < self.user_soc_target:
                if self.charging_mode != CHARGING_MODE_NIGHT_F3:
                    _LOGGER.info("F3 tariff active – starting night charging (target SOC %.0f%%)", self.user_soc_target)
                    await self._set_wallbox_mode(MQTT_MODE_NORMAL)
                    night_a = self._watts_to_amps(self.night_power_limit_w, data.get("wallbox_voltage_v", 230.0))
                    await self.set_current_limit(night_a)
                    await self.authorize_charging()
                    self.charging_mode = CHARGING_MODE_NIGHT_F3
                    self.solar_controller_active = False
                else:
                    # Maintain night limit with load balancing
                    max_a = min(
                        self._watts_to_amps(self.night_power_limit_w, data.get("wallbox_voltage_v", 230.0)),
                        await self._compute_load_balanced_current()
                    )
                    await self._send_limit_if_changed(max_a)
            else:
                if self.charging_mode == CHARGING_MODE_NIGHT_F3:
                    _LOGGER.info("Night charging complete at SOC %.0f%% – stopping", vehicle_soc)
                    await self.revoke_charging()
                    self.charging_mode = CHARGING_MODE_IDLE
            self.async_update_listeners()
            return

        # ── 4. PV SURPLUS CHARGING
        surplus_w = self.pv_surplus_w
        voltage = data.get("wallbox_voltage_v", 230.0)
        surplus_a = self._watts_to_amps(surplus_w + self.allowed_import_w, voltage)

        if surplus_a >= DEFAULT_MIN_CHARGE_CURRENT_A:
            if vehicle_soc < self.vehicle_soc_target:
                if self.charging_mode != CHARGING_MODE_PV_SURPLUS:
                    _LOGGER.info("PV surplus %.0fW available – starting solar charging", surplus_w)
                    await self._set_wallbox_mode(MQTT_MODE_SOLAR)
                    capped_a = min(surplus_a, await self._compute_load_balanced_current())
                    await self.set_current_limit(capped_a)
                    await self.authorize_charging()
                    self.charging_mode = CHARGING_MODE_PV_SURPLUS
                    self.solar_controller_active = True
                else:
                    # Dynamic adjustment
                    capped_a = min(surplus_a, await self._compute_load_balanced_current())
                    await self._send_limit_if_changed(capped_a)
            else:
                if self.charging_mode == CHARGING_MODE_PV_SURPLUS:
                    _LOGGER.info("Vehicle SOC %.0f%% reached target – stopping PV charging", vehicle_soc)
                    await self.revoke_charging()
                    self.charging_mode = CHARGING_MODE_IDLE
                    self.solar_controller_active = False
        else:
            # Not enough surplus
            if self.charging_mode == CHARGING_MODE_PV_SURPLUS:
                _LOGGER.info("PV surplus dropped below minimum – pausing charging")
                await self._set_wallbox_mode(MQTT_MODE_PAUSE)
                await self.revoke_charging()
                self.charging_mode = CHARGING_MODE_IDLE
                self.solar_controller_active = False

        self.async_update_listeners()

    # ------------------------------------------------------------------
    # Load balancing helpers
    # ------------------------------------------------------------------
    async def _compute_load_balanced_current(self) -> float:
        """Compute maximum allowed charging current based on contract limit."""
        data = self.data or {}
        wallbox_power_w = data.get("wallbox_power_w", 0.0)
        grid_w = data.get("grid_power_w", 0.0)
        voltage = data.get("wallbox_voltage_v", 230.0)

        # Total house load excluding wallbox
        pv_w = data.get("pv_power_w", 0.0)
        house_load_w = max(0.0, grid_w + pv_w - wallbox_power_w)

        available_for_ev_w = self._contract_power_w - house_load_w - DEFAULT_SAFETY_MARGIN_W
        max_a = self._watts_to_amps(available_for_ev_w, voltage)
        clamped = min(DEFAULT_MAX_CHARGE_CURRENT_A, max(DEFAULT_MIN_CHARGE_CURRENT_A, max_a))
        return round(clamped, 1)

    async def _send_limit_if_changed(self, current_a: float) -> None:
        """Send current limit to wallbox only if it changed to reduce MQTT traffic."""
        if abs(current_a - self.last_limit_sent_a) >= 0.5:
            await self.set_current_limit(current_a)

    @staticmethod
    def _watts_to_amps(watts: float, voltage: float) -> float:
        """Convert watts to amps."""
        if voltage <= 0:
            return 0.0
        return watts / voltage

    # ------------------------------------------------------------------
    # MQTT command helpers
    # ------------------------------------------------------------------
    async def authorize_charging(self) -> None:
        """Send charging authorization command via MQTT."""
        topic = f"{self._mqtt_base}/command/authorize"
        await mqtt.async_publish(self.hass, topic, "1", qos=1, retain=False)
        self.last_authorization_ts = datetime.now()
        _LOGGER.debug("Authorization sent on %s", topic)

    async def revoke_charging(self) -> None:
        """Send charging revocation command via MQTT."""
        topic = f"{self._mqtt_base}/command/revoke"
        await mqtt.async_publish(self.hass, topic, "1", qos=1, retain=False)
        self.last_revoke_ts = datetime.now()
        _LOGGER.debug("Revocation sent on %s", topic)

    async def set_current_limit(self, current_a: float) -> None:
        """Send current limit to the wallbox via MQTT."""
        clamped = int(min(DEFAULT_MAX_CHARGE_CURRENT_A, max(DEFAULT_MIN_CHARGE_CURRENT_A, current_a)))
        topic = f"{self._mqtt_base}/command/set_current_limit"
        await mqtt.async_publish(self.hass, topic, str(clamped), qos=1, retain=False)
        self.last_limit_sent_a = clamped
        _LOGGER.debug("Current limit %dA sent on %s", clamped, topic)

    async def _set_wallbox_mode(self, mode: int) -> None:
        """Set wallbox operating mode (1=Solar, 2=Normal, 3=Pause)."""
        topic = f"{self._mqtt_base}/command/set_mode"
        await mqtt.async_publish(self.hass, topic, str(mode), qos=1, retain=False)
        _LOGGER.debug("Wallbox mode %d sent on %s", mode, topic)

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------
    def _get_state(self, entity_id: str, default: str = "unknown") -> str:
        state = self.hass.states.get(entity_id)
        if state is None:
            return default
        return state.state

    def _get_float(self, entity_id: str, default: float = 0.0) -> float:
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", ""):
            return default
        try:
            return float(state.state)
        except (ValueError, TypeError):
            return default

    def _get_bool(self, entity_id: str, default: bool = False) -> bool:
        state = self.hass.states.get(entity_id)
        if state is None:
            return default
        return state.state in ("on", "true", "connected", "yes", "1")
