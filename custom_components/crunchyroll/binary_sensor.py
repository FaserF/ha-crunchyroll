from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CrunchyrollDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Crunchyroll binary sensors based on a config entry."""
    coordinator: CrunchyrollDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            CrunchyrollPremiumBinarySensor(coordinator, entry),
        ]
    )


class CrunchyrollPremiumBinarySensor(
    CoordinatorEntity[CrunchyrollDataUpdateCoordinator], BinarySensorEntity
):
    """Binary sensor for Crunchyroll Premium / Active subscription status."""

    _attr_has_entity_name = True
    _attr_translation_key = "premium"
    _attr_icon = "mdi:star-circle"

    def __init__(
        self,
        coordinator: CrunchyrollDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        account_id = coordinator.data.profile.account_id or entry.entry_id
        self._attr_unique_id = f"{account_id}_premium"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, account_id)},
            name=f"Crunchyroll ({coordinator.data.profile.profile_name or coordinator.data.profile.username or 'Account'})",
            manufacturer="Crunchyroll",
            model="Streaming Account",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.crunchyroll.com",
        )

    @property
    def is_on(self) -> bool:
        """Return true if account has an active premium subscription."""
        if not self.coordinator.data or not self.coordinator.data.subscription:
            return False
        return self.coordinator.data.subscription.is_premium

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return subscription attributes."""
        if not self.coordinator.data or not self.coordinator.data.subscription:
            return {}
        sub = self.coordinator.data.subscription
        return {
            "tier": sub.tier,
            "products": sub.products,
        }
