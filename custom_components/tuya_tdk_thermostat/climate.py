from __future__ import annotations

import logging
from typing import Any, Dict, Optional, List

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_DEVICE_IDS,
    TEMP_SCALE,
    DP_SWITCH,
    DP_MODE,
    DP_TEMP_SET,
    DP_TEMP_CURRENT,
    DP_UPPER_TEMP,
    DP_LOWER_TEMP,
    DP_WORK_STATE,
    DP_CHILD_LOCK,
    DP_FROST,
    DP_BATTERY_PCT,
    DP_WORK_DAYS,
    DP_QDWENCHA,
    DP_DORMANT_SWITCH,
    DP_DORMANT_TIME_SET,
    DP_FACTORY_RESET,
    DP_WEEK_UP_BTN,
    DP_WEEK_PROGRAM3,
)
from .coordinator import TuyaThermostatCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: TuyaThermostatCoordinator = data["coordinator"]
    device_ids = data["device_ids"]

    entities = [TuyaTDKThermostatEntity(coordinator, dev_id) for dev_id in device_ids]
    async_add_entities(entities, True)


def _scale_from_dev(val: Optional[float]) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val) * TEMP_SCALE
    except Exception:
        return None

def _scale_to_dev(val_c: float) -> int:
    return int(round(val_c / TEMP_SCALE))


class TuyaTDKThermostatEntity(CoordinatorEntity[TuyaThermostatCoordinator], ClimateEntity):
    _attr_should_poll = False
    _attr_temperature_unit = TEMP_CELSIUS

    def __init__(self, coordinator: TuyaThermostatCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"tuya_tdk_thermostat_{device_id}"
        self._attr_name = f"Tuya Thermostat {device_id[-6:]}"
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
        self._attr_min_temp = 5.0
        self._attr_max_temp = 30.0

    def _status(self) -> Dict[str, Any]:
        return self.coordinator.data.get(self._device_id, {}) or {}

    def _get(self, code: str, default: Any = None) -> Any:
        return self._status().get(code, default)

    def _bool(self, code: str) -> Optional[bool]:
        val = self._get(code)
        return bool(val) if isinstance(val, bool) else None

    @property
    def current_temperature(self) -> Optional[float]:
        return _scale_from_dev(self._get(DP_TEMP_CURRENT))

    @property
    def target_temperature(self) -> Optional[float]:
        return _scale_from_dev(self._get(DP_TEMP_SET))

    @property
    def min_temp(self) -> float:
        lo = self._get(DP_LOWER_TEMP)
        return _scale_from_dev(lo) or self._attr_min_temp

    @property
    def max_temp(self) -> float:
        hi = self._get(DP_UPPER_TEMP)
        return _scale_from_dev(hi) or self._attr_max_temp

    @property
    def hvac_mode(self) -> HVACMode:
        sw = self._bool(DP_SWITCH)
        if sw is False:
            return HVACMode.OFF
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> Optional[str]:
        """
        Uses work_state; maps 'heating' -> heating, 'stop' -> idle, off when hvac_mode is OFF.
        """
        if self.hvac_mode == HVACMode.OFF:
            return "off"

        ws = self._get(DP_WORK_STATE)
        if isinstance(ws, str):
            l = ws.lower()
            if l == "heating":
                return "heating"
            if l == "stop":
                return "idle"

        cur = self.current_temperature
        tgt = self.target_temperature
        if cur is not None and tgt is not None:
            return "heating" if cur < tgt else "idle"
        return None

    @property
    def preset_mode(self) -> Optional[str]:
        mode = self._get(DP_MODE)
        if isinstance(mode, str):
            return mode.lower()
        return None

    @property
    def preset_modes(self) -> List[str]:
        mode = self._get(DP_MODE)
        observed = set()
        if isinstance(mode, str):
            observed.add(mode.lower())
        common = {"home", "away", "auto", "manual", "schedule", "comfort", "eco"}
        return sorted(observed.union(common))

    async def async_set_temperature(self, **kwargs) -> None:
        tgt = kwargs.get(ATTR_TEMPERATURE)
        if tgt is None:
            return
        tgt = max(self.min_temp, min(self.max_temp, float(tgt)))
        dev_val = _scale_to_dev(tgt)
        cmds = [{"code": DP_TEMP_SET, "value": dev_val}]
        client = self.coordinator._client  # type: ignore[attr-defined]
        ok = await self.hass.async_add_executor_job(client.send_commands, self._device_id, cmds)
        if ok:
            await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        cmds = []
        if hvac_mode == HVACMode.OFF:
            cmds.append({"code": DP_SWITCH, "value": False})
        elif hvac_mode == HVACMode.HEAT:
            cmds.append({"code": DP_SWITCH, "value": True})
        else:
            _LOGGER.debug("Unsupported hvac_mode=%s for device=%s", hvac_mode, self._device_id)
            return

        client = self.coordinator._client  # type: ignore[attr-defined]
        ok = await self.hass.async_add_executor_job(client.send_commands, self._device_id, cmds)
        if ok:
            await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if not isinstance(preset_mode, str):
            return
        cmds = [{"code": DP_MODE, "value": preset_mode.lower()}]
        client = self.coordinator._client  # type: ignore[attr-defined]
        ok = await self.hass.async_add_executor_job(client.send_commands, self._device_id, cmds)
        if ok:
            await self.coordinator.async_request_refresh()

    @property
    def supported_features(self) -> int:
        return self._attr_supported_features

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        attrs: Dict[str, Any] = {
            "device_id": self._device_id,
            "tuya_dp": self._status(),
        }
        attrs["child_lock"] = self._get(DP_CHILD_LOCK)
        attrs["frost"] = self._get(DP_FROST)
        attrs["battery_percentage"] = self._get(DP_BATTERY_PCT)
        attrs["work_days"] = self._get(DP_WORK_DAYS)
        attrs["hysteresis_qidongwencha"] = self._get(DP_QDWENCHA)
        attrs["dormant_switch"] = self._get(DP_DORMANT_SWITCH)
        attrs["dormant_time_set_raw"] = self._get(DP_DORMANT_TIME_SET)
        attrs["factory_reset_flag"] = self._get(DP_FACTORY_RESET)
        attrs["week_up_btn"] = self._get(DP_WEEK_UP_BTN)
        attrs["week_program3_raw"] = self._get(DP_WEEK_PROGRAM3)
        return attrs
