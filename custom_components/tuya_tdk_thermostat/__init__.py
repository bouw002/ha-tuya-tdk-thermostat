import logging
from typing import Any, Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_ACCESS_ID, CONF_ACCESS_SECRET, CONF_ENDPOINT, CONF_DEVICE_IDS
from .api import TuyaTDKClient
from .coordinator import TuyaThermostatCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data: Dict[str, Any] = dict(entry.data)

    access_id = data[CONF_ACCESS_ID]
    access_secret = data[CONF_ACCESS_SECRET]
    endpoint = data[CONF_ENDPOINT]
    device_ids = data[CONF_DEVICE_IDS]

    client = TuyaTDKClient(endpoint, access_id, access_secret)

    # Connect to Tuya Cloud (blocking)
    await hass.async_add_executor_job(client.connect)

    coordinator = TuyaThermostatCoordinator(hass, client, device_ids)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "device_ids": device_ids,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
