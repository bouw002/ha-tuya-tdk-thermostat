import logging
from datetime import timedelta
from typing import Dict, Any, List

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TuyaTDKClient
from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

class TuyaThermostatCoordinator(DataUpdateCoordinator[Dict[str, Dict[str, Any]]]):
    """
    Polls Tuya Cloud for each device's status.
    data => { device_id: { dp_code: value, ...}, ... }
    """

    def __init__(self, hass: HomeAssistant, client: TuyaTDKClient, device_ids: List[str]) -> None:
        self._client = client
        self._device_ids = device_ids
        super().__init__(
            hass,
            _LOGGER,
            name="Tuya Thermostat Coordinator",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> Dict[str, Dict[str, Any]]:
        results: Dict[str, Dict[str, Any]] = {}
        try:
            for device_id in self._device_ids:
                status = await self.hass.async_add_executor_job(
                    self._client.get_device_status_map, device_id
                )
                results[device_id] = status or {}
            return results
        except Exception as err:
            raise UpdateFailed(str(err)) from err
