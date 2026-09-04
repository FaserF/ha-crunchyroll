from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.client import CrunchyrollClient
from .api.exceptions import AuthenticationError, ConnectionError, CrunchyrollError
from .api.models import CrunchyrollData
from .const import (
    CONF_AUTO_REMOVE_WATCHED_FROM_WATCHLIST,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_CRUNCHYROLL_NEW_EPISODE_AVAILABLE,
    EVENT_CRUNCHYROLL_WATCHLIST_UPDATED,
)

_LOGGER = logging.getLogger(__name__)


class CrunchyrollDataUpdateCoordinator(DataUpdateCoordinator[CrunchyrollData]):
    """Coordinator to manage fetching Crunchyroll data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: CrunchyrollClient,
        config_entry: ConfigEntry | None = None,
        update_interval_seconds: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval_seconds),
        )
        self.client = client
        self._previous_watchlist_ids: set[str] | None = None
        self._previous_episode_ids: set[str] | None = None

    async def _async_update_data(self) -> CrunchyrollData:
        """Fetch all data from Crunchyroll API."""
        try:
            data = await self.client.fetch_all_data()
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(
                f"Crunchyroll authentication failed: {err}"
            ) from err
        except ConnectionError as err:
            raise UpdateFailed(
                f"Connection error fetching Crunchyroll data: {err}"
            ) from err
        except CrunchyrollError as err:
            raise UpdateFailed(f"Error fetching Crunchyroll data: {err}") from err

        # Detect new watchlist additions and fire event
        current_ids = {it.id for it in data.watchlist}
        if self._previous_watchlist_ids is not None:
            added_ids = current_ids - self._previous_watchlist_ids
            if added_ids:
                new_items = [it for it in data.watchlist if it.id in added_ids]
                for item in new_items:
                    self.hass.bus.async_fire(
                        EVENT_CRUNCHYROLL_WATCHLIST_UPDATED,
                        {
                            "action": "added",
                            "account_id": data.profile.account_id,
                            "id": item.id,
                            "title": item.title,
                            "type": item.type,
                            "image_url": item.image_url,
                            "description": item.description,
                        },
                    )
        self._previous_watchlist_ids = current_ids

        # Detect new episodes for watched anime and fire event
        current_ep_ids = {ep.id for ep in data.new_episodes_for_watched}
        if self._previous_episode_ids is not None:
            newly_detected_ep_ids = current_ep_ids - self._previous_episode_ids
            if newly_detected_ep_ids:
                new_ep_items = [
                    ep
                    for ep in data.new_episodes_for_watched
                    if ep.id in newly_detected_ep_ids
                ]
                for ep in new_ep_items:
                    self.hass.bus.async_fire(
                        EVENT_CRUNCHYROLL_NEW_EPISODE_AVAILABLE,
                        {
                            "account_id": data.profile.account_id,
                            "episode_id": ep.id,
                            "series_id": ep.series_id,
                            "series_title": ep.series_title,
                            "episode_title": ep.title,
                            "episode_number": ep.episode_number,
                            "season_number": ep.season_number,
                            "release_date": ep.release_date,
                            "image_url": ep.image_url,
                            "url": ep.crunchyroll_url,
                        },
                    )
        self._previous_episode_ids = current_ep_ids

        # If configured, automatically remove completed anime from watchlist
        if self.config_entry and self.config_entry.options.get(
            CONF_AUTO_REMOVE_WATCHED_FROM_WATCHLIST, False
        ):
            await self._async_clean_completed_from_watchlist_items(data)

        return data

    async def _async_clean_completed_from_watchlist_items(
        self, data: CrunchyrollData
    ) -> list[str]:
        """Remove completed anime from the watchlist using provided data."""
        completed_ids = {
            item.series_id for item in data.completed_animes if item.series_id
        }
        removed_titles: list[str] = []
        for wl_item in list(data.watchlist):
            target_id = wl_item.series_id or wl_item.id
            if target_id and target_id in completed_ids:
                try:
                    await self.client.remove_from_watchlist(target_id)
                    data.watchlist.remove(wl_item)
                    removed_titles.append(wl_item.title)
                    _LOGGER.info(
                        "Removed completed anime '%s' (%s) from watchlist",
                        wl_item.title,
                        target_id,
                    )
                except CrunchyrollError as err:
                    _LOGGER.warning(
                        "Failed to remove '%s' from watchlist: %s",
                        wl_item.title,
                        err,
                    )
        return removed_titles

    async def async_clean_completed_from_watchlist(self) -> list[str]:
        """Manually trigger removing completed anime from watchlist and refresh state."""
        if not self.data:
            await self.async_request_refresh()
            return []
        removed = await self._async_clean_completed_from_watchlist_items(self.data)
        if removed:
            self.async_update_listeners()
        return removed
