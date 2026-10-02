"""Select platform for Crunchyroll profile switching."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PROFILE_ID, DOMAIN
from .coordinator import CrunchyrollDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Crunchyroll select entity based on a config entry."""
    coordinator: CrunchyrollDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CrunchyrollProfileSelect(coordinator, entry)])


class CrunchyrollProfileSelect(
    CoordinatorEntity[CrunchyrollDataUpdateCoordinator], SelectEntity
):
    """Select entity to switch active Crunchyroll profile."""

    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: CrunchyrollDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the profile select entity."""
        super().__init__(coordinator)
        self._entry = entry
        account_id = coordinator.data.profile.account_id or entry.entry_id
        self._attr_unique_id = f"{account_id}_profile"
        self._attr_translation_key = "profile"
        self._attr_icon = "mdi:account-switch"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, account_id)},
            name=f"Crunchyroll ({coordinator.data.profile.profile_name or coordinator.data.profile.username or 'Account'})",
            manufacturer="Crunchyroll",
            model="Streaming Account",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.crunchyroll.com",
        )

    @property
    def _profile_map(self) -> dict[str, str]:
        """Map of profile name to profile_id."""
        profiles = self.coordinator.data.profiles
        if not profiles:
            p = self.coordinator.data.profile
            name = p.profile_name or p.username or "Primary"
            pid = p.profile_id or p.account_id
            return {name: pid}
        return {
            (p.profile_name or p.username or p.profile_id): (
                p.profile_id or p.account_id
            )
            for p in profiles
        }

    @property
    def options(self) -> list[str]:
        """Return available profile options."""
        return list(self._profile_map.keys())

    @property
    def current_option(self) -> str | None:
        """Return the current active profile name."""
        active_pid = (
            self.coordinator.client.profile_id
            or self.coordinator.data.profile.profile_id
        )
        for name, pid in self._profile_map.items():
            if pid == active_pid:
                return name
        return (
            self.coordinator.data.profile.profile_name
            or self.coordinator.data.profile.username
            or None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "active_profile_id": self.coordinator.client.profile_id
            or self.coordinator.data.profile.profile_id,
            "profiles": [
                {
                    "profile_id": p.profile_id,
                    "profile_name": p.profile_name,
                    "username": p.username,
                    "avatar": p.avatar,
                    "is_primary": p.is_primary,
                }
                for p in self.coordinator.data.profiles
            ],
        }

    async def async_select_option(self, option: str) -> None:
        """Switch to selected profile."""
        profile_id = self._profile_map.get(option)
        if not profile_id:
            _LOGGER.warning("Profile '%s' not found in available options", option)
            return

        await self.coordinator.client.switch_profile(profile_id)
        # Update config entry options/data to persist selection
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={**self._entry.options, CONF_PROFILE_ID: profile_id},
        )
        await self.coordinator.async_request_refresh()
