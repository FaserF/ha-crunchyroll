"""Media player platform for Crunchyroll integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    BrowseMedia,
    MediaClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.components.media_player.errors import BrowseError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CrunchyrollDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

MEDIA_TYPE_CR_ROOT = "crunchyroll_root"
MEDIA_TYPE_CR_CONTINUE_WATCHING = "continue_watching"
MEDIA_TYPE_CR_WATCHLIST = "watchlist"
MEDIA_TYPE_CR_SIMULCASTS = "simulcasts"
MEDIA_TYPE_CR_POPULAR = "popular"
MEDIA_TYPE_CR_NEW = "new"
MEDIA_TYPE_CR_CATEGORIES = "categories"
MEDIA_TYPE_CR_CATEGORY = "category"
MEDIA_TYPE_CR_SERIES = "series"
MEDIA_TYPE_CR_SEASON = "season"
MEDIA_TYPE_CR_EPISODE = "episode"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Crunchyroll media player based on a config entry."""
    coordinator: CrunchyrollDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CrunchyrollMediaPlayer(coordinator, entry)])


class CrunchyrollMediaPlayer(
    CoordinatorEntity[CrunchyrollDataUpdateCoordinator], MediaPlayerEntity
):
    """Crunchyroll Media Player entity supporting browsing and media playback dispatch."""

    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "media_player"
    _attr_icon = "mdi:play-circle-outline"
    _attr_supported_features = (
        MediaPlayerEntityFeature.BROWSE_MEDIA | MediaPlayerEntityFeature.PLAY_MEDIA
    )

    def __init__(
        self,
        coordinator: CrunchyrollDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the Crunchyroll media player."""
        super().__init__(coordinator)
        self._entry = entry
        account_id = coordinator.data.profile.account_id or entry.entry_id
        self._attr_unique_id = f"{account_id}_media_player"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, account_id)},
            name=f"Crunchyroll ({coordinator.data.profile.profile_name or coordinator.data.profile.username or 'Account'})",
            manufacturer="Crunchyroll",
            model="Streaming Account",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.crunchyroll.com",
        )
        self._attr_state = MediaPlayerState.IDLE
        self._attr_media_title = None
        self._attr_media_series_title = None
        self._attr_media_season = None
        self._attr_media_episode = None
        self._attr_media_image_url = None
        self._attr_media_content_id = None
        self._attr_media_content_type = MediaType.VIDEO

    @property
    def client(self):
        """Return the API client."""
        return self.coordinator.client

    async def async_browse_media(
        self,
        media_content_type: str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """Browse media library."""
        if media_content_id is None or media_content_type in (None, MEDIA_TYPE_CR_ROOT):
            return await self._build_root_browser()

        parts = media_content_id.split(":", 1)
        browse_type = parts[0]
        browse_arg = parts[1] if len(parts) > 1 else ""

        if browse_type == MEDIA_TYPE_CR_CONTINUE_WATCHING:
            return await self._build_continue_watching_browser()
        if browse_type == MEDIA_TYPE_CR_WATCHLIST:
            return await self._build_watchlist_browser()
        if browse_type == MEDIA_TYPE_CR_SIMULCASTS:
            return await self._build_simulcasts_browser()
        if browse_type == MEDIA_TYPE_CR_POPULAR:
            return await self._build_popular_browser()
        if browse_type == MEDIA_TYPE_CR_NEW:
            return await self._build_new_browser()
        if browse_type == MEDIA_TYPE_CR_CATEGORIES:
            return await self._build_categories_browser()
        if browse_type == MEDIA_TYPE_CR_CATEGORY:
            return await self._build_category_browser(browse_arg)
        if browse_type == MEDIA_TYPE_CR_SERIES:
            return await self._build_series_browser(browse_arg)
        if browse_type == MEDIA_TYPE_CR_SEASON:
            return await self._build_season_browser(browse_arg)

        raise BrowseError(f"Media not found: {media_content_type} / {media_content_id}")

    async def _build_root_browser(self) -> BrowseMedia:
        """Build root directory for browsing."""
        children = [
            BrowseMedia(
                title="Continue Watching",
                media_class=MediaClass.DIRECTORY,
                media_content_id=f"{MEDIA_TYPE_CR_CONTINUE_WATCHING}:",
                media_content_type=MEDIA_TYPE_CR_CONTINUE_WATCHING,
                can_play=False,
                can_expand=True,
                thumbnail=None,
            ),
            BrowseMedia(
                title="Watchlist",
                media_class=MediaClass.DIRECTORY,
                media_content_id=f"{MEDIA_TYPE_CR_WATCHLIST}:",
                media_content_type=MEDIA_TYPE_CR_WATCHLIST,
                can_play=False,
                can_expand=True,
                thumbnail=None,
            ),
            BrowseMedia(
                title="Simulcasts",
                media_class=MediaClass.DIRECTORY,
                media_content_id=f"{MEDIA_TYPE_CR_SIMULCASTS}:",
                media_content_type=MEDIA_TYPE_CR_SIMULCASTS,
                can_play=False,
                can_expand=True,
                thumbnail=None,
            ),
            BrowseMedia(
                title="Popular Anime",
                media_class=MediaClass.DIRECTORY,
                media_content_id=f"{MEDIA_TYPE_CR_POPULAR}:",
                media_content_type=MEDIA_TYPE_CR_POPULAR,
                can_play=False,
                can_expand=True,
                thumbnail=None,
            ),
            BrowseMedia(
                title="New Releases",
                media_class=MediaClass.DIRECTORY,
                media_content_id=f"{MEDIA_TYPE_CR_NEW}:",
                media_content_type=MEDIA_TYPE_CR_NEW,
                can_play=False,
                can_expand=True,
                thumbnail=None,
            ),
            BrowseMedia(
                title="Categories & Genres",
                media_class=MediaClass.DIRECTORY,
                media_content_id=f"{MEDIA_TYPE_CR_CATEGORIES}:",
                media_content_type=MEDIA_TYPE_CR_CATEGORIES,
                can_play=False,
                can_expand=True,
                thumbnail=None,
            ),
        ]
        return BrowseMedia(
            title="Crunchyroll",
            media_class=MediaClass.DIRECTORY,
            media_content_id=f"{MEDIA_TYPE_CR_ROOT}:",
            media_content_type=MEDIA_TYPE_CR_ROOT,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _build_continue_watching_browser(self) -> BrowseMedia:
        """Browse items in Continue Watching."""
        cw_items = await self.client.get_continue_watching(25)
        children = [
            BrowseMedia(
                title=item.display_title,
                media_class=MediaClass.EPISODE,
                media_content_id=f"{MEDIA_TYPE_CR_EPISODE}:{item.id}",
                media_content_type=MediaType.VIDEO,
                can_play=True,
                can_expand=False,
                thumbnail=item.image_url,
            )
            for item in cw_items
        ]
        return BrowseMedia(
            title="Continue Watching",
            media_class=MediaClass.DIRECTORY,
            media_content_id=f"{MEDIA_TYPE_CR_CONTINUE_WATCHING}:",
            media_content_type=MEDIA_TYPE_CR_CONTINUE_WATCHING,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _build_watchlist_browser(self) -> BrowseMedia:
        """Browse items in Watchlist."""
        wl_items = await self.client.get_watchlist(50)
        children = []
        for item in wl_items:
            series_id = item.series_id or item.id
            children.append(
                BrowseMedia(
                    title=item.series_title or item.title,
                    media_class=MediaClass.TV_SHOW,
                    media_content_id=f"{MEDIA_TYPE_CR_SERIES}:{series_id}",
                    media_content_type=MediaType.TVSHOW,
                    can_play=False,
                    can_expand=True,
                    thumbnail=item.image_url,
                )
            )
        return BrowseMedia(
            title="Watchlist",
            media_class=MediaClass.DIRECTORY,
            media_content_id=f"{MEDIA_TYPE_CR_WATCHLIST}:",
            media_content_type=MEDIA_TYPE_CR_WATCHLIST,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _build_simulcasts_browser(self) -> BrowseMedia:
        """Browse simulcast season anime."""
        simulcasts = await self.client.get_simulcasts(30)
        children = [
            BrowseMedia(
                title=item.title,
                media_class=MediaClass.TV_SHOW,
                media_content_id=f"{MEDIA_TYPE_CR_SERIES}:{item.id}",
                media_content_type=MediaType.TVSHOW,
                can_play=False,
                can_expand=True,
                thumbnail=item.image_url,
            )
            for item in simulcasts
            if item.title
        ]
        return BrowseMedia(
            title="Simulcasts",
            media_class=MediaClass.DIRECTORY,
            media_content_id=f"{MEDIA_TYPE_CR_SIMULCASTS}:",
            media_content_type=MEDIA_TYPE_CR_SIMULCASTS,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _build_popular_browser(self) -> BrowseMedia:
        """Browse popular anime series."""
        popular = await self.client.get_popular_animes(30)
        children = [
            BrowseMedia(
                title=item.title,
                media_class=MediaClass.TV_SHOW,
                media_content_id=f"{MEDIA_TYPE_CR_SERIES}:{item.id}",
                media_content_type=MediaType.TVSHOW,
                can_play=False,
                can_expand=True,
                thumbnail=item.image_url,
            )
            for item in popular
            if item.title
        ]
        return BrowseMedia(
            title="Popular Anime",
            media_class=MediaClass.DIRECTORY,
            media_content_id=f"{MEDIA_TYPE_CR_POPULAR}:",
            media_content_type=MEDIA_TYPE_CR_POPULAR,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _build_new_browser(self) -> BrowseMedia:
        """Browse newly added releases."""
        new_items = await self.client.get_new_animes(30)
        children = [
            BrowseMedia(
                title=item.title,
                media_class=MediaClass.TV_SHOW,
                media_content_id=f"{MEDIA_TYPE_CR_SERIES}:{item.id}",
                media_content_type=MediaType.TVSHOW,
                can_play=False,
                can_expand=True,
                thumbnail=item.image_url,
            )
            for item in new_items
            if item.title
        ]
        return BrowseMedia(
            title="New Releases",
            media_class=MediaClass.DIRECTORY,
            media_content_id=f"{MEDIA_TYPE_CR_NEW}:",
            media_content_type=MEDIA_TYPE_CR_NEW,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _build_categories_browser(self) -> BrowseMedia:
        """Browse available categories / genres."""
        cats = await self.client.get_categories()
        children = [
            BrowseMedia(
                title=c.localization or c.id,
                media_class=MediaClass.DIRECTORY,
                media_content_id=f"{MEDIA_TYPE_CR_CATEGORY}:{c.id}",
                media_content_type=MEDIA_TYPE_CR_CATEGORY,
                can_play=False,
                can_expand=True,
                thumbnail=None,
            )
            for c in cats
        ]
        return BrowseMedia(
            title="Categories & Genres",
            media_class=MediaClass.DIRECTORY,
            media_content_id=f"{MEDIA_TYPE_CR_CATEGORIES}:",
            media_content_type=MEDIA_TYPE_CR_CATEGORIES,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _build_category_browser(self, category_id: str) -> BrowseMedia:
        """Browse items in a specific category."""
        items = await self.client.get_category_items(category_id, limit=30)
        children = [
            BrowseMedia(
                title=item.title,
                media_class=MediaClass.TV_SHOW,
                media_content_id=f"{MEDIA_TYPE_CR_SERIES}:{item.id}",
                media_content_type=MediaType.TVSHOW,
                can_play=False,
                can_expand=True,
                thumbnail=item.image_url,
            )
            for item in items
            if item.title
        ]
        return BrowseMedia(
            title=category_id.capitalize(),
            media_class=MediaClass.DIRECTORY,
            media_content_id=f"{MEDIA_TYPE_CR_CATEGORY}:{category_id}",
            media_content_type=MEDIA_TYPE_CR_CATEGORY,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _build_series_browser(self, series_id: str) -> BrowseMedia:
        """Browse seasons in a series."""
        seasons = await self.client.get_series_seasons(series_id)
        children = [
            BrowseMedia(
                title=s.get("title") or f"Season {s.get('season_number', '')}",
                media_class=MediaClass.SEASON,
                media_content_id=f"{MEDIA_TYPE_CR_SEASON}:{s.get('id')}",
                media_content_type=MediaType.SEASON,
                can_play=False,
                can_expand=True,
                thumbnail=None,
            )
            for s in seasons
            if s.get("id")
        ]
        return BrowseMedia(
            title="Seasons",
            media_class=MediaClass.TV_SHOW,
            media_content_id=f"{MEDIA_TYPE_CR_SERIES}:{series_id}",
            media_content_type=MediaType.TVSHOW,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def _build_season_browser(self, season_id: str) -> BrowseMedia:
        """Browse episodes in a season."""
        episodes = await self.client.get_season_episodes(season_id)
        children = []
        for ep in episodes:
            ep_id = ep.get("id")
            if not ep_id:
                continue
            ep_num = ep.get("episode_number") or ep.get("episode")
            ep_title = ep.get("title") or "Episode"
            display = f"Ep. {ep_num}: {ep_title}" if ep_num else ep_title

            img_url = None
            images = ep.get("images", {})
            for key in ["thumbnail", "poster_tall", "poster_wide"]:
                if key in images and images[key] and isinstance(images[key], list):
                    last_group = images[key][-1]
                    if isinstance(last_group, list) and last_group:
                        img_url = last_group[-1].get("source")
                    elif isinstance(last_group, dict):
                        img_url = last_group.get("source")
                    if img_url:
                        break

            children.append(
                BrowseMedia(
                    title=display,
                    media_class=MediaClass.EPISODE,
                    media_content_id=f"{MEDIA_TYPE_CR_EPISODE}:{ep_id}",
                    media_content_type=MediaType.VIDEO,
                    can_play=True,
                    can_expand=False,
                    thumbnail=img_url,
                )
            )
        return BrowseMedia(
            title="Episodes",
            media_class=MediaClass.SEASON,
            media_content_id=f"{MEDIA_TYPE_CR_SEASON}:{season_id}",
            media_content_type=MediaType.SEASON,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def async_play_media(
        self,
        media_type: str,
        media_id: str,
        **kwargs: Any,
    ) -> None:
        """Play media (sets media player state and dispatches playback URL/link)."""
        content_id = media_id.split(":", 1)[-1] if ":" in media_id else media_id
        url = f"https://www.crunchyroll.com/watch/{content_id}"

        self._attr_state = MediaPlayerState.PLAYING
        self._attr_media_content_id = url
        self._attr_media_content_type = MediaType.VIDEO
        self._attr_media_title = f"Episode {content_id}"
        self.async_write_ha_state()
