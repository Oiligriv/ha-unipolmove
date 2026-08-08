"""The Unipolmove integration."""
from __future__ import annotations

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import UnipolmoveApiClient, UnipolmoveApiError, UnipolmoveAuthError
from .const import CONF_CONTRACT_ID, CONF_PASSWORD, CONF_USERNAME, DOMAIN
from .coordinator import UnipolmoveCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_create_clientsession(hass)
    api = UnipolmoveApiClient(
        session,
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_CONTRACT_ID],
    )
    # Both outcomes have to be told apart here, or the entry just fails to set
    # up: a rejected password needs the reauth flow, while an unreachable site
    # only needs Home Assistant to try again later.
    try:
        await api.async_login()
    except UnipolmoveAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except (UnipolmoveApiError, aiohttp.ClientError, TimeoutError) as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = UnipolmoveCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
