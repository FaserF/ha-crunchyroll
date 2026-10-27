from __future__ import annotations

import logging
import re
import urllib.parse
from datetime import timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.client import CrunchyrollClient
from .api.exceptions import AuthenticationError, ConnectionError, CrunchyrollError
from .api.models import CrunchyrollData
from .const import (
    CONF_AUTO_REMOVE_WATCHED_FROM_WATCHLIST,
    CONF_SUGGESTARR_ENABLED,
    CONF_SUGGESTARR_TMDB_API_KEY,
    CONF_SUGGESTARR_URL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SUGGESTARR_ENABLED,
    DEFAULT_SUGGESTARR_URL,
    DEFAULT_TMDB_API_KEY,
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
        self._synced_suggestarr_titles: set[str] = set()

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
        except Exception as err:
            raise UpdateFailed(
                f"Unexpected error fetching crunchyroll data: {err}"
            ) from err

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

        # Sync watched items to Suggestarr if enabled
        try:
            await self.async_sync_watched_to_suggestarr()
        except Exception as err:
            _LOGGER.warning("Error auto-syncing watched anime to Suggestarr: %s", err)

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

    @staticmethod
    def _clean_series_title(title: str) -> str:
        """Strip language, dub, sub, and format markers from anime titles."""
        cleaned = re.sub(
            r"\s*(\([^\)]*(?:Dub|Sub|OmU|OV|Ger|Eng|Jap)[^\)]*\)|\[[^\]]*(?:Dub|Sub|OmU|OV|Ger|Eng|Jap)[^\]]*\])",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()
        return cleaned or title

    async def async_sync_watched_to_suggestarr(self, force_all: bool = False) -> int:
        """Sync watched Crunchyroll anime series to Suggestarr."""
        if not self.config_entry:
            return 0

        enabled = self.config_entry.options.get(
            CONF_SUGGESTARR_ENABLED, DEFAULT_SUGGESTARR_ENABLED
        )
        if not enabled:
            _LOGGER.debug("Suggestarr sync is disabled in options")
            return 0

        if not self.data:
            return 0

        suggestarr_url = (
            self.config_entry.options.get(CONF_SUGGESTARR_URL, DEFAULT_SUGGESTARR_URL)
            or ""
        ).rstrip("/")
        tmdb_api_key = (
            self.config_entry.options.get(
                CONF_SUGGESTARR_TMDB_API_KEY, DEFAULT_TMDB_API_KEY
            )
            or ""
        )

        if not suggestarr_url:
            _LOGGER.debug("Suggestarr sync skipped: URL not configured")
            return 0

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "HomeAssistant-Crunchyroll/1.0",
        }

        # Lazy initialize or refresh synced titles from Suggestarr
        async with aiohttp.ClientSession() as session:
            if not self._synced_suggestarr_titles or force_all:
                try:
                    async with session.get(
                        f"{suggestarr_url}/api/watched-history/me",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=15),
                        ssl=False,
                    ) as resp:
                        if resp.status == 200:
                            res_json = await resp.json()
                            items = res_json.get("items", [])
                            for it in items:
                                if it.get("title"):
                                    self._synced_suggestarr_titles.add(
                                        it["title"].strip().lower()
                                    )
                                if it.get("tmdb_id"):
                                    self._synced_suggestarr_titles.add(
                                        str(it["tmdb_id"])
                                    )
                except Exception as err:
                    _LOGGER.warning(
                        "Could not fetch existing watched items from Suggestarr: %s",
                        err,
                    )

            # Collect all unique candidate series from watch history and progress
            candidate_titles: list[str] = []
            seen_clean: set[str] = set()

            for prog in self.data.completed_animes:
                t = prog.series_title or prog.episode_title
                if t:
                    c = self._clean_series_title(t)
                    if c.lower() not in seen_clean:
                        seen_clean.add(c.lower())
                        candidate_titles.append(c)

            for prog in self.data.in_progress_animes:
                t = prog.series_title or prog.episode_title
                if t:
                    c = self._clean_series_title(t)
                    if c.lower() not in seen_clean:
                        seen_clean.add(c.lower())
                        candidate_titles.append(c)

            for it in self.data.history:
                t = it.series_title or it.title
                if t:
                    c = self._clean_series_title(t)
                    if c.lower() not in seen_clean:
                        seen_clean.add(c.lower())
                        candidate_titles.append(c)

            synced_count = 0
            for title in candidate_titles:
                clean_lower = title.lower()
                if clean_lower in self._synced_suggestarr_titles:
                    continue

                # Search via Suggestarr internal TMDb proxy first, fallback to direct TMDb API if key provided
                try:
                    search_q = urllib.parse.quote(title)
                    matched_id = None
                    matched_title = title
                    matched_year = None
                    matched_type = "tv"

                    # 1. Try Suggestarr internal search proxy (/api/watched-history/me/search)
                    try:
                        async with session.get(
                            f"{suggestarr_url}/api/watched-history/me/search?query={search_q}&media_type=both",
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=10),
                            ssl=False,
                        ) as sg_search_resp:
                            if sg_search_resp.status == 200:
                                sg_data = await sg_search_resp.json()
                                sg_results = sg_data.get("results", [])
                                if sg_results:
                                    best_res = sg_results[0]
                                    for r in sg_results:
                                        if (
                                            r.get("title") or ""
                                        ).strip().lower() == clean_lower:
                                            best_res = r
                                            break
                                    if best_res.get("tmdb_id"):
                                        matched_id = str(best_res["tmdb_id"])
                                        matched_title = best_res.get("title") or title
                                        matched_type = (
                                            best_res.get("media_type") or "tv"
                                        )
                                        y_val = best_res.get("year")
                                        matched_year = (
                                            int(y_val)
                                            if y_val and str(y_val).isdigit()
                                            else None
                                        )
                    except Exception as sg_err:
                        _LOGGER.debug(
                            "Suggestarr proxy search failed for '%s': %s", title, sg_err
                        )

                    # 2. Fallback to direct TMDb search if Suggestarr proxy returned no result and API key is present
                    if not matched_id and tmdb_api_key:
                        tmdb_url = f"https://api.themoviedb.org/3/search/multi?api_key={tmdb_api_key}&query={search_q}&include_adult=false"
                        async with session.get(
                            tmdb_url,
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as tmdb_resp:
                            if tmdb_resp.status == 200:
                                tmdb_data = await tmdb_resp.json()
                                results = tmdb_data.get("results", [])
                                for res in results:
                                    if res.get("media_type") in ("tv", "movie"):
                                        matched_id = str(res.get("id"))
                                        matched_title = (
                                            res.get("name") or res.get("title") or title
                                        )
                                        matched_type = res.get("media_type", "tv")
                                        date_str = (
                                            res.get("first_air_date")
                                            or res.get("release_date")
                                            or ""
                                        )
                                        matched_year = (
                                            int(date_str[:4])
                                            if date_str
                                            and len(date_str) >= 4
                                            and date_str[:4].isdigit()
                                            else None
                                        )
                                        break

                    if not matched_id:
                        self._synced_suggestarr_titles.add(clean_lower)
                        continue

                    str_id = str(matched_id)
                    if str_id in self._synced_suggestarr_titles:
                        self._synced_suggestarr_titles.add(clean_lower)
                        continue

                    tmdb_id = int(matched_id) if matched_id.isdigit() else matched_id

                    post_payload = {
                        "tmdb_id": tmdb_id,
                        "media_type": matched_type,
                        "title": matched_title,
                        "year": matched_year,
                    }

                    async with session.post(
                        f"{suggestarr_url}/api/watched-history/me",
                        json=post_payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=15),
                        ssl=False,
                    ) as post_resp:
                        if post_resp.status in (200, 201):
                            synced_count += 1
                            self._synced_suggestarr_titles.add(clean_lower)
                            self._synced_suggestarr_titles.add(str_id)
                            _LOGGER.info(
                                "Synced '%s' (TMDb: %s) to Suggestarr",
                                matched_title,
                                tmdb_id,
                            )
                        else:
                            resp_err = await post_resp.text()
                            _LOGGER.warning(
                                "Suggestarr returned %s for '%s': %s",
                                post_resp.status,
                                matched_title,
                                resp_err,
                            )
                except Exception as sync_err:
                    _LOGGER.warning(
                        "Error syncing '%s' to Suggestarr: %s",
                        title,
                        sync_err,
                    )

            return synced_count
