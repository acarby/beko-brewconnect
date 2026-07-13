"""The Beko BrewConnect integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client

from .coffee_sdk.client import TuyaCloudClient
from .const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_DEVICE_ID, CONF_REGION
from .coordinator import BrewConnectCoordinator

PLATFORMS = ["sensor", "binary_sensor", "button"]

type BrewConnectConfigEntry = ConfigEntry[BrewConnectCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: BrewConnectConfigEntry) -> bool:
    client = TuyaCloudClient(
        entry.data[CONF_CLIENT_ID],
        entry.data[CONF_CLIENT_SECRET],
        region=entry.data[CONF_REGION],
        http_client=get_async_client(hass),
    )
    coordinator = BrewConnectCoordinator(hass, client, entry.data[CONF_DEVICE_ID])
    await coordinator.async_load_history()
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BrewConnectConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.client.aclose()
    return unload_ok
