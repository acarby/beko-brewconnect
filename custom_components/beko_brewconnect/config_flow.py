"""Config flow for Beko BrewConnect."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.httpx_client import get_async_client

from .coffee_sdk.client import TuyaCloudClient
from .coffee_sdk.exceptions import APIError, AuthenticationError
from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DEVICE_ID,
    CONF_REGION,
    DEFAULT_REGION,
    DOMAIN,
    REGIONS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CLIENT_ID): str,
        vol.Required(CONF_CLIENT_SECRET): str,
        vol.Required(CONF_DEVICE_ID): str,
        vol.Required(CONF_REGION, default=DEFAULT_REGION): vol.In(REGIONS),
    }
)


class BrewConnectConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Beko BrewConnect."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()

            client = TuyaCloudClient(
                user_input[CONF_CLIENT_ID],
                user_input[CONF_CLIENT_SECRET],
                region=user_input[CONF_REGION],
                http_client=get_async_client(self.hass),
            )
            try:
                machine = client.machine(user_input[CONF_DEVICE_ID])
                info = await machine.info()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except APIError:
                errors["base"] = "device_not_found"
            except Exception:
                _LOGGER.exception("Unexpected error validating BrewConnect device")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info.name, data=user_input)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)
