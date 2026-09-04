from __future__ import annotations

import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api.client import CrunchyrollClient
from .const import (
    CONF_AUDIO_LOCALE,
    CONF_EMAIL,
    CONF_LOCALE,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    DEFAULT_AUDIO_LOCALE,
    DEFAULT_LOCALE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import CrunchyrollDataUpdateCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: Final[list[Platform]] = [
    Platform.SENSOR,
    Platform.CALENDAR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Crunchyroll from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    locale = entry.options.get(
        CONF_LOCALE,
        entry.data.get(CONF_LOCALE, DEFAULT_LOCALE),
    )
    audio_locale = entry.options.get(
        CONF_AUDIO_LOCALE,
        entry.data.get(CONF_AUDIO_LOCALE, DEFAULT_AUDIO_LOCALE),
    )

    client = CrunchyrollClient(
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        locale=locale,
        preferred_audio_language=audio_locale,
    )

    coordinator = CrunchyrollDataUpdateCoordinator(
        hass,
        client,
        config_entry=entry,
        update_interval_seconds=scan_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await async_setup_services(hass)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: CrunchyrollDataUpdateCoordinator = hass.data[DOMAIN].pop(
            entry.entry_id
        )
        await coordinator.client.close()

    if not hass.data[DOMAIN]:
        await async_unload_services(hass)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
