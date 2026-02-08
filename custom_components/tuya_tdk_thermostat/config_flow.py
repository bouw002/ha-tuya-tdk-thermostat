from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_ENDPOINT,
    CONF_DEVICE_IDS,
)
from .api import TuyaTDKClient

_LOGGER = logging.getLogger(__name__)

REGION_HINTS = {
    "EU": "https://openapi.tuyaeu.com",
    "US": "https://openapi.tuyaus.com",
    "CN": "https://openapi.tuyacn.com",
    "IN": "https://openapi.tuyain.com",
}

class TuyaTDKConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._user_input: Dict[str, Any] = {}
        self._client: Optional[TuyaTDKClient] = None
        self._devices: List[Dict[str, Any]] = []

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(CONF_ACCESS_ID): str,
                    vol.Required(CONF_ACCESS_SECRET): str,
                    vol.Required(CONF_ENDPOINT, default=REGION_HINTS["EU"]): str,
                }
            )
            return self.async_show_form(step_id="user", data_schema=schema)

        self._user_input.update(user_input)

        client = TuyaTDKClient(
            user_input[CONF_ENDPOINT],
            user_input[CONF_ACCESS_ID],
            user_input[CONF_ACCESS_SECRET],
        )

        try:
            await self.hass.async_add_executor_job(client.connect)
            self._devices = await self.hass.async_add_executor_job(client.list_devices)
            self._client = client
        except Exception:
            _LOGGER.exception("Failed to connect to Tuya Cloud")
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_ACCESS_ID, default=user_input[CONF_ACCESS_ID]): str,
                        vol.Required(CONF_ACCESS_SECRET, default=user_input[CONF_ACCESS_SECRET]): str,
                        vol.Required(CONF_ENDPOINT, default=user_input[CONF_ENDPOINT]): str,
                    }
                ),
                errors={"base": "cannot_connect"},
            )

        # Allow selecting any devices (not all are thermostats; user decides)
        candidate_ids = [dev.get("id") for dev in self._devices if isinstance(dev, dict) and dev.get("id")]
        if not candidate_ids:
            return self.async_abort(reason="no_devices_found")

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_IDS): vol.All(vol.Unique(), [vol.In(candidate_ids)])
            }
        )
        return self.async_show_form(step_id="select_devices", data_schema=schema)

    async def async_step_select_devices(self, user_input: Dict[str, Any]):
        self._user_input.update(user_input)

        title = "Tuya TDK Thermostat"
        await self.async_set_unique_id(f"{self._user_input[CONF_ACCESS_ID]}_{self._user_input[CONF_ENDPOINT]}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=title,
            data={
                CONF_ACCESS_ID: self._user_input[CONF_ACCESS_ID],
                CONF_ACCESS_SECRET: self._user_input[CONF_ACCESS_SECRET],
                CONF_ENDPOINT: self._user_input[CONF_ENDPOINT],
                CONF_DEVICE_IDS: self._user_input[CONF_DEVICE_IDS],
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return TuyaTDKOptionsFlow(config_entry)


class TuyaTDKOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return self.async_create_entry(title="", data={})
