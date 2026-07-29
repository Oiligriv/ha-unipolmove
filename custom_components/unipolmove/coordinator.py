"""Data coordinator for the Unipolmove integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import UnipolmoveApiClient, UnipolmoveApiError, UnipolmoveAuthError, UnipolmoveData
from .const import DOMAIN, UPDATE_INTERVAL_HOURS

_LOGGER = logging.getLogger(__name__)


class UnipolmoveCoordinator(DataUpdateCoordinator[UnipolmoveData]):
    """Fetches Unipolmove invoice/cost data on a schedule, re-logging in as needed."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: UnipolmoveApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(hours=UPDATE_INTERVAL_HOURS),
        )
        self.entry = entry
        self.api = api

    async def _async_update_data(self) -> UnipolmoveData:
        try:
            return await self.api.async_get_data()
        except UnipolmoveAuthError:
            # Session cookie expired - the login itself has no CAPTCHA, so a
            # fresh login can be retried automatically without user input.
            try:
                await self.api.async_login()
                return await self.api.async_get_data()
            except UnipolmoveAuthError as err:
                raise ConfigEntryAuthFailed(str(err)) from err
        except UnipolmoveApiError as err:
            raise UpdateFailed(str(err)) from err
