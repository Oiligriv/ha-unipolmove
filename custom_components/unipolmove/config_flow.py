"""Config flow for the Unipolmove integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import UnipolmoveApiClient, UnipolmoveApiError, UnipolmoveAuthError
from .const import CONF_CONTRACT_ID, CONF_PASSWORD, CONF_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_CONTRACT_ID): str,
    }
)


class UnipolmoveConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Unipolmove."""

    VERSION = 1

    async def _validate(self, username: str, password: str, contract_id: str):
        session = async_create_clientsession(self.hass)
        api = UnipolmoveApiClient(session, username, password, contract_id)
        await api.async_login()
        return await api.async_get_data()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await self._validate(
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                    user_input[CONF_CONTRACT_ID],
                )
            except UnipolmoveAuthError:
                errors["base"] = "invalid_auth"
            except UnipolmoveApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating Unipolmove credentials")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_CONTRACT_ID])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_CONTRACT_ID], data=user_input
                )

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            try:
                await self._validate(
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                    reauth_entry.data[CONF_CONTRACT_ID],
                )
            except UnipolmoveAuthError:
                errors["base"] = "invalid_auth"
            except UnipolmoveApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating Unipolmove credentials")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data={**reauth_entry.data, **user_input},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )
