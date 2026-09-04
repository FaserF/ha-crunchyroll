from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ACCOUNT_ID,
    ATTR_CATEGORIES,
    ATTR_COMPLETED_ANIMES,
    ATTR_CUSTOM_LISTS,
    ATTR_EMAIL,
    ATTR_EMAIL_VERIFIED,
    ATTR_HISTORY_COUNT,
    ATTR_IN_PROGRESS_ANIMES,
    ATTR_IS_PREMIUM,
    ATTR_ITEMS,
    ATTR_LAST_WATCHED,
    ATTR_MATURITY_RATING,
    ATTR_MOVIES,
    ATTR_NEW_ANIMES,
    ATTR_NEW_EPISODES,
    ATTR_NEW_EPISODES_FOR_WATCHED,
    ATTR_POPULAR_ANIMES,
    ATTR_PRODUCTS,
    ATTR_PROFILE_ID,
    ATTR_PROFILE_NAME,
    ATTR_RECOMMENDATIONS,
    ATTR_SIMULCASTS,
    ATTR_SUBSCRIPTION_TIER,
    ATTR_WATCHLIST,
    ATTR_WATCHLIST_COUNT,
    DOMAIN,
)
from .coordinator import CrunchyrollDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Crunchyroll sensors based on a config entry."""
    coordinator: CrunchyrollDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            CrunchyrollAccountSensor(coordinator, entry),
            CrunchyrollWatchlistSensor(coordinator, entry),
            CrunchyrollCompletedAnimesSensor(coordinator, entry),
            CrunchyrollInProgressAnimesSensor(coordinator, entry),
            CrunchyrollNewAnimesSensor(coordinator, entry),
            CrunchyrollPopularAnimesSensor(coordinator, entry),
            CrunchyrollSimulcastsSensor(coordinator, entry),
            CrunchyrollMoviesSensor(coordinator, entry),
            CrunchyrollNewEpisodesForWatchedSensor(coordinator, entry),
            CrunchyrollNewEpisodesSensor(coordinator, entry),
            CrunchyrollCustomListsSensor(coordinator, entry),
        ]
    )


class _BaseCrunchyrollSensor(
    CoordinatorEntity[CrunchyrollDataUpdateCoordinator], SensorEntity
):
    """Base class for Crunchyroll sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CrunchyrollDataUpdateCoordinator,
        entry: ConfigEntry,
        unique_suffix: str,
        translation_key: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        account_id = coordinator.data.profile.account_id or entry.entry_id
        self._attr_unique_id = f"{account_id}_{unique_suffix}"
        self._attr_translation_key = translation_key
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, account_id)},
            name=f"Crunchyroll ({coordinator.data.profile.profile_name or coordinator.data.profile.username or 'Account'})",
            manufacturer="Crunchyroll",
            model="Streaming Account",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.crunchyroll.com",
        )


class CrunchyrollAccountSensor(_BaseCrunchyrollSensor):
    """Consolidated Crunchyroll Account sensor containing status and rich attributes."""

    def __init__(
        self,
        coordinator: CrunchyrollDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            unique_suffix="account",
            translation_key="account",
            icon="mdi:account-circle",
        )

    @property
    def native_value(self) -> str:
        """Return the subscription tier / active status as state."""
        if not self.coordinator.data or not self.coordinator.data.profile:
            return "unknown"
        sub = self.coordinator.data.subscription
        if sub.is_premium:
            return sub.tier or "premium"
        return "free"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return attributes including profile, subscription, watchlist, history and recommendations."""
        if not self.coordinator.data:
            return {}

        data = self.coordinator.data
        prof = data.profile
        sub = data.subscription

        last_watched_dict: dict[str, Any] = {}
        if data.history:
            last = data.history[0]
            last_watched_dict = {
                "id": last.id,
                "title": last.title,
                "display_title": last.display_title,
                "episode_number": last.episode_number,
                "season_title": last.season_title,
                "image_url": last.image_url,
                "playhead_seconds": last.last_playhead_secs,
                "duration_ms": last.duration_ms,
                "is_completed": last.is_completed,
            }

        watchlist_items = [
            {
                "id": item.id,
                "title": item.title,
                "type": item.type,
                "image_url": item.image_url,
                "description": item.description,
            }
            for item in data.watchlist[:25]
        ]

        recommendations_items = [
            {
                "id": item.id,
                "title": item.title,
                "type": item.type,
                "image_url": item.image_url,
                "description": item.description,
            }
            for item in data.recommendations[:15]
        ]

        return {
            ATTR_ACCOUNT_ID: prof.account_id,
            ATTR_PROFILE_ID: prof.profile_id or prof.account_id,
            ATTR_PROFILE_NAME: prof.profile_name or prof.username,
            ATTR_EMAIL: prof.email,
            ATTR_EMAIL_VERIFIED: prof.email_verified,
            ATTR_IS_PREMIUM: sub.is_premium,
            ATTR_SUBSCRIPTION_TIER: sub.tier,
            ATTR_PRODUCTS: sub.products,
            ATTR_MATURITY_RATING: prof.maturity_rating,
            ATTR_WATCHLIST_COUNT: len(data.watchlist),
            ATTR_WATCHLIST: watchlist_items,
            ATTR_HISTORY_COUNT: data.total_history_count or len(data.history),
            ATTR_LAST_WATCHED: last_watched_dict,
            ATTR_RECOMMENDATIONS: recommendations_items,
            ATTR_CUSTOM_LISTS: [cl.to_dict() for cl in data.custom_lists],
            ATTR_CATEGORIES: [c.to_dict() for c in data.categories],
        }


class CrunchyrollWatchlistSensor(_BaseCrunchyrollSensor):
    """Sensor displaying current watchlist count and items."""

    def __init__(
        self,
        coordinator: CrunchyrollDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            unique_suffix="watchlist",
            translation_key="watchlist",
            icon="mdi:bookmark-multiple",
        )

    @property
    def native_value(self) -> int:
        """Return the number of items in the watchlist."""
        if not self.coordinator.data:
            return 0
        return len(self.coordinator.data.watchlist)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return all watchlist items with rich attributes."""
        if not self.coordinator.data:
            return {}

        items = [item.to_dict() for item in self.coordinator.data.watchlist]
        latest = items[0] if items else {}

        return {
            ATTR_WATCHLIST_COUNT: len(items),
            "latest_added_title": latest.get("title", ""),
            "latest_added_id": latest.get("id", ""),
            "latest_added_image": latest.get("image_url", ""),
            "latest_added_url": latest.get("url", ""),
            ATTR_ITEMS: items,
        }


class CrunchyrollCompletedAnimesSensor(_BaseCrunchyrollSensor):
    """Sensor displaying watched / completed animes."""

    def __init__(
        self,
        coordinator: CrunchyrollDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            unique_suffix="completed_animes",
            translation_key="completed_animes",
            icon="mdi:check-circle-outline",
        )

    @property
    def native_value(self) -> int:
        """Return the count of completed anime entries."""
        if not self.coordinator.data:
            return 0
        return len(self.coordinator.data.completed_animes)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return list of completed animes with details."""
        if not self.coordinator.data:
            return {}
        items = [a.to_dict() for a in self.coordinator.data.completed_animes]
        latest = items[0] if items else {}
        return {
            "count": len(items),
            "latest_completed_series": latest.get("series_title", ""),
            "latest_completed_episode": latest.get("episode_title", ""),
            "latest_completed_episode_number": latest.get("episode_number", ""),
            "latest_completed_image": latest.get("image_url", ""),
            "latest_completed_date": latest.get("date_played", ""),
            "latest_completed_url": latest.get("url", ""),
            ATTR_COMPLETED_ANIMES: items,
        }


class CrunchyrollInProgressAnimesSensor(_BaseCrunchyrollSensor):
    """Sensor displaying in-progress (started but not finished) animes."""

    def __init__(
        self,
        coordinator: CrunchyrollDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            unique_suffix="in_progress_animes",
            translation_key="in_progress_animes",
            icon="mdi:progress-clock",
        )

    @property
    def native_value(self) -> int:
        """Return the count of in-progress anime entries."""
        if not self.coordinator.data:
            return 0
        return len(self.coordinator.data.in_progress_animes)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return list of in-progress animes with details."""
        if not self.coordinator.data:
            return {}
        items = [a.to_dict() for a in self.coordinator.data.in_progress_animes]
        latest = items[0] if items else {}
        return {
            "count": len(items),
            "latest_series": latest.get("series_title", ""),
            "latest_episode": latest.get("episode_title", ""),
            "latest_episode_number": latest.get("episode_number", ""),
            "latest_playhead_seconds": latest.get("playhead_seconds", 0),
            "latest_progress_percent": latest.get("progress_percent", 0),
            "latest_image": latest.get("image_url", ""),
            "latest_url": latest.get("url", ""),
            ATTR_IN_PROGRESS_ANIMES: items,
        }


class CrunchyrollNewAnimesSensor(_BaseCrunchyrollSensor):
    """Sensor displaying newly added anime releases."""

    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: CrunchyrollDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            unique_suffix="new_animes",
            translation_key="new_animes",
            icon="mdi:new-box",
        )

    @property
    def native_value(self) -> int:
        """Return the count of new anime releases available."""
        if not self.coordinator.data:
            return 0
        return len(self.coordinator.data.new_animes)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return list of newly released animes."""
        if not self.coordinator.data:
            return {}
        items = [item.to_dict() for item in self.coordinator.data.new_animes]
        latest = items[0] if items else {}
        return {
            "count": len(items),
            "latest_release_title": latest.get("title", ""),
            "latest_release_id": latest.get("id", ""),
            "latest_release_image": latest.get("image_url", ""),
            "latest_release_description": latest.get("description", ""),
            "latest_release_url": latest.get("url", ""),
            ATTR_NEW_ANIMES: items,
        }


class CrunchyrollPopularAnimesSensor(_BaseCrunchyrollSensor):
    """Sensor displaying popular / trending anime on Crunchyroll."""

    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: CrunchyrollDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            unique_suffix="popular_animes",
            translation_key="popular_animes",
            icon="mdi:fire",
        )

    @property
    def native_value(self) -> int:
        """Return the count of popular anime entries."""
        if not self.coordinator.data:
            return 0
        return len(self.coordinator.data.popular_animes)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return list of popular animes."""
        if not self.coordinator.data:
            return {}
        items = [item.to_dict() for item in self.coordinator.data.popular_animes]
        latest = items[0] if items else {}
        return {
            "count": len(items),
            "top_popular_title": latest.get("title", ""),
            "top_popular_id": latest.get("id", ""),
            "top_popular_image": latest.get("image_url", ""),
            "top_popular_url": latest.get("url", ""),
            ATTR_POPULAR_ANIMES: items,
        }


class CrunchyrollCustomListsSensor(_BaseCrunchyrollSensor):
    """Sensor displaying user custom anime lists / crunchylists."""

    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: CrunchyrollDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            unique_suffix="custom_lists",
            translation_key="custom_lists",
            icon="mdi:playlist-star",
        )

    @property
    def native_value(self) -> int:
        """Return the count of user custom lists."""
        if not self.coordinator.data:
            return 0
        return len(self.coordinator.data.custom_lists)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return list of custom lists with metadata."""
        if not self.coordinator.data:
            return {}
        items = [cl.to_dict() for cl in self.coordinator.data.custom_lists]
        return {
            "count": len(items),
            ATTR_CUSTOM_LISTS: items,
        }


class CrunchyrollSimulcastsSensor(_BaseCrunchyrollSensor):
    """Sensor displaying seasonal simulcast anime."""

    def __init__(
        self,
        coordinator: CrunchyrollDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            unique_suffix="simulcasts",
            translation_key="simulcasts",
            icon="mdi:television-guide",
        )

    @property
    def native_value(self) -> int:
        """Return the count of simulcasts."""
        if not self.coordinator.data:
            return 0
        return len(self.coordinator.data.simulcasts)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return list of simulcast animes."""
        if not self.coordinator.data:
            return {}
        items = [item.to_dict() for item in self.coordinator.data.simulcasts]
        latest = items[0] if items else {}
        return {
            "count": len(items),
            "latest_simulcast_title": latest.get("title", ""),
            "latest_simulcast_id": latest.get("id", ""),
            "latest_simulcast_image": latest.get("image_url", ""),
            "latest_simulcast_url": latest.get("url", ""),
            ATTR_SIMULCASTS: items,
        }


class CrunchyrollMoviesSensor(_BaseCrunchyrollSensor):
    """Sensor displaying available anime movies."""

    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: CrunchyrollDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            unique_suffix="movies",
            translation_key="movies",
            icon="mdi:filmstrip",
        )

    @property
    def native_value(self) -> int:
        """Return the count of movies."""
        if not self.coordinator.data:
            return 0
        return len(self.coordinator.data.movies)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return list of movies."""
        if not self.coordinator.data:
            return {}
        items = [item.to_dict() for item in self.coordinator.data.movies]
        latest = items[0] if items else {}
        return {
            "count": len(items),
            "latest_movie_title": latest.get("title", ""),
            "latest_movie_id": latest.get("id", ""),
            "latest_movie_image": latest.get("image_url", ""),
            "latest_movie_url": latest.get("url", ""),
            ATTR_MOVIES: items,
        }


class CrunchyrollNewEpisodesForWatchedSensor(_BaseCrunchyrollSensor):
    """Sensor displaying new episodes for user's watched/watchlist anime."""

    def __init__(
        self,
        coordinator: CrunchyrollDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            unique_suffix="new_episodes_for_watched",
            translation_key="new_episodes_for_watched",
            icon="mdi:bell-ring-outline",
        )

    @property
    def native_value(self) -> int:
        """Return the count of new episodes for watched anime."""
        if not self.coordinator.data:
            return 0
        return len(self.coordinator.data.new_episodes_for_watched)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return list of new episodes for watched anime."""
        if not self.coordinator.data:
            return {}
        items = [
            item.to_dict() for item in self.coordinator.data.new_episodes_for_watched
        ]
        latest = items[0] if items else {}
        return {
            "count": len(items),
            "latest_episode_title": latest.get("title", ""),
            "latest_series_title": latest.get("series_title", ""),
            "latest_episode_number": latest.get("episode_number", ""),
            "latest_release_date": latest.get("release_date", ""),
            "latest_image_url": latest.get("image_url", ""),
            "latest_url": latest.get("url", ""),
            ATTR_NEW_EPISODES_FOR_WATCHED: items,
        }


class CrunchyrollNewEpisodesSensor(_BaseCrunchyrollSensor):
    """Sensor displaying all newly added anime episodes."""

    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: CrunchyrollDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            unique_suffix="new_episodes",
            translation_key="new_episodes",
            icon="mdi:television-box",
        )

    @property
    def native_value(self) -> int:
        """Return the count of newly released episodes."""
        if not self.coordinator.data:
            return 0
        return len(self.coordinator.data.new_episodes)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return list of new episodes."""
        if not self.coordinator.data:
            return {}
        items = [item.to_dict() for item in self.coordinator.data.new_episodes]
        latest = items[0] if items else {}
        return {
            "count": len(items),
            "latest_episode_title": latest.get("title", ""),
            "latest_series_title": latest.get("series_title", ""),
            "latest_episode_number": latest.get("episode_number", ""),
            "latest_release_date": latest.get("release_date", ""),
            "latest_image_url": latest.get("image_url", ""),
            "latest_url": latest.get("url", ""),
            ATTR_NEW_EPISODES: items,
        }
