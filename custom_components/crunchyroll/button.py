from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CrunchyrollDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Crunchyroll button based on a config entry."""
    coordinator: CrunchyrollDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CrunchyrollCleanWatchlistButton(coordinator, entry)])


class CrunchyrollCleanWatchlistButton(
    CoordinatorEntity[CrunchyrollDataUpdateCoordinator], ButtonEntity
):
    """Button to remove all watched animes from the user's watchlist."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CrunchyrollDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the clean watchlist button."""
        super().__init__(coordinator)
        self._entry = entry
        account_id = coordinator.data.profile.account_id or entry.entry_id
        self._attr_unique_id = f"{account_id}_clean_watchlist"
        self._attr_translation_key = "clean_watchlist"
        self._attr_icon = "mdi:playlist-remove"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, account_id)},
            name=f"Crunchyroll ({coordinator.data.profile.profile_name or coordinator.data.profile.username or 'Account'})",
            manufacturer="Crunchyroll",
            model="Streaming Account",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.crunchyroll.com",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_clean_completed_from_watchlist()
