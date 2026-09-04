from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
import jwt

from .exceptions import (
    AuthenticationError,
    ConnectionError,
    CrunchyrollError,
    RateLimitError,
)
from .models import (
    AnimeProgress,
    Category,
    CrunchyrollData,
    CrunchyrollItem,
    CrunchyrollProfile,
    CrunchyrollSubscription,
    CustomList,
)

_LOGGER = logging.getLogger(__name__)

# Active Crunchyroll client basic authentication token
PUBLIC_TOKEN = (
    "eHVuaWh2ZWRidDNtYmlzdWhldnQ6MWtJUzVkeVR2akUwX3JxYUEzWWVBaDBiVVhVbXhXMTE="
)
BASE_URL = "https://beta-api.crunchyroll.com"


class CrunchyrollClient:
    """Async API Client for Crunchyroll using native REST OAuth2 endpoints."""

    def __init__(
        self,
        email: str,
        password: str,
        locale: str = "en-US",
        preferred_audio_language: str = "ja-JP",
        device_id: str | None = None,
        device_name: str = "HomeAssistant",
        device_type: str = "Home Assistant Integration",
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_expiry: float | None = None,
        account_id: str | None = None,
        profile_id: str | None = None,
        external_id: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.email = email
        self.password = password
        self.locale = locale
        self.preferred_audio_language = preferred_audio_language
        self.device_id = device_id or str(uuid4())
        self.device_name = device_name
        self.device_type = device_type

        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expiry = token_expiry
        self.account_id = account_id
        self.profile_id = profile_id
        self.external_id = external_id

        self._client = http_client or httpx.AsyncClient(timeout=20.0)
        self._owns_client = http_client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @property
    def is_authorized(self) -> bool:
        return bool(self.access_token and self.refresh_token)

    async def login(self) -> bool:
        payload = {
            "username": self.email,
            "password": self.password,
            "grant_type": "password",
            "scope": "offline_access",
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
        }
        headers = {
            "Authorization": f"Basic {PUBLIC_TOKEN}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        try:
            resp = await self._client.post(
                f"{BASE_URL}/auth/v1/token",
                data=payload,
                headers=headers,
            )
        except httpx.TransportError as err:
            raise ConnectionError(
                f"Failed to connect to Crunchyroll auth: {err}"
            ) from err

        if resp.status_code in (200, 201):
            data = resp.json()
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            if data.get("account_id"):
                self.account_id = data.get("account_id")
            expires = data.get("expires_in", 3888000)
            self.token_expiry = datetime.now(UTC).timestamp() + expires - 60
            return True

        if resp.status_code in (400, 401):
            raise AuthenticationError("Invalid Crunchyroll credentials")
        if resp.status_code == 429:
            raise RateLimitError("Rate limit exceeded while authenticating.")
        raise CrunchyrollError(
            f"Authentication failed ({resp.status_code}): {resp.text}"
        )

    async def refresh_tokens_if_needed(self) -> None:
        if not self.access_token or not self.refresh_token:
            await self.login()
            return
        now_ts = datetime.now(UTC).timestamp()
        if self.token_expiry and now_ts < self.token_expiry:
            return
        payload = {
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
            "scope": "offline_access",
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
        }
        headers = {
            "Authorization": f"Basic {PUBLIC_TOKEN}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        try:
            resp = await self._client.post(
                f"{BASE_URL}/auth/v1/token",
                data=payload,
                headers=headers,
            )
        except httpx.TransportError as err:
            raise ConnectionError(f"Failed to refresh token: {err}") from err

        if resp.status_code == 200:
            data = resp.json()
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            expires = data.get("expires_in", 3888000)
            self.token_expiry = now_ts + expires - 60
            return
        _LOGGER.warning("Token refresh failed, attempting login")
        await self.login()

    async def request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        retried: bool = False,
    ) -> Any:
        await self.refresh_tokens_if_needed()
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        url = f"{BASE_URL}/{endpoint.lstrip('/')}"
        try:
            resp = await self._client.request(
                method,
                url,
                params=params,
                json=json_data,
                headers=headers,
            )
        except httpx.TransportError as err:
            raise ConnectionError(f"Connection failed to {url}: {err}") from err

        if resp.status_code == 401 and not retried:
            self.token_expiry = 0
            await self.refresh_tokens_if_needed()
            return await self.request(method, endpoint, params, json_data, retried=True)
        if resp.status_code == 429:
            raise RateLimitError(f"Rate limited on {endpoint}")
        if resp.status_code in (200, 201, 204):
            if resp.status_code == 204 or not resp.text:
                return {}
            return resp.json()
        raise CrunchyrollError(
            f"API error {resp.status_code} on {endpoint}: {resp.text}"
        )

    async def get_profiles(self) -> list[CrunchyrollProfile]:
        """Fetch all profiles associated with the account."""
        try:
            data = await self.request("GET", "accounts/v1/me/multiprofile")
            profiles_raw = data.get("profiles", [])
            profiles = [CrunchyrollProfile.from_dict(p) for p in profiles_raw]
            if profiles:
                return profiles
        except CrunchyrollError:
            _LOGGER.debug(
                "Failed to fetch multiprofile, falling back to single profile"
            )

        # Fallback to single profile
        single = await self.get_profile()
        return [single]

    async def get_profile(self) -> CrunchyrollProfile:
        me_data: dict[str, Any] = {}
        try:
            me_data = await self.request("GET", "accounts/v1/me")
            if me_data:
                self.account_id = me_data.get("account_id", self.account_id or "")
                self.external_id = str(
                    me_data.get("external_id", self.external_id or "")
                )
        except CrunchyrollError:
            pass

        try:
            data = await self.request("GET", "accounts/v1/me/profile")
        except CrunchyrollError:
            data = me_data or await self.request("GET", "auth/v1/me")
        self.account_id = data.get("account_id", self.account_id or "")

        # Merge account-level fields (like email_verified and external_id) from /accounts/v1/me
        if me_data:
            if "email_verified" in me_data:
                data["email_verified"] = me_data["email_verified"]
            if "external_id" in me_data:
                data["external_id"] = me_data["external_id"]

        # If a specific profile_id is configured and differs from primary, try to fetch it from multiprofile
        if self.profile_id and self.profile_id != data.get("profile_id"):
            try:
                prof_data = await self.request(
                    "GET", f"accounts/v1/me/multiprofile/{self.profile_id}"
                )
                if prof_data:
                    if me_data:
                        prof_data["email_verified"] = me_data.get(
                            "email_verified", False
                        )
                        prof_data["external_id"] = me_data.get("external_id", "")
                    return CrunchyrollProfile.from_dict(prof_data, self.account_id)
            except CrunchyrollError:
                _LOGGER.warning(
                    "Failed to fetch profile %s, falling back to primary",
                    self.profile_id,
                )

        return CrunchyrollProfile.from_dict(data, self.account_id)

    async def get_subscription(self) -> CrunchyrollSubscription:
        if not self.account_id:
            await self.get_profile()

        # Extract benefits claim from access token JWT if present
        token_benefits: list[str] = []
        if self.access_token:
            try:
                claims = jwt.decode(
                    self.access_token, options={"verify_signature": False}
                )
                token_benefits = claims.get("benefits", [])
            except Exception:  # noqa: BLE001
                token_benefits = []

        sub_data: dict[str, Any] = {}
        # Try external_id first (used by iTunes/App Store/Google Play/web subs) then account_id
        ids_to_try = [id_ for id_ in (self.external_id, self.account_id) if id_]
        for sub_id in ids_to_try:
            try:
                data = await self.request(
                    "GET", f"subs/v1/subscriptions/{sub_id}/products"
                )
                if data and (data.get("items") or isinstance(data, list)):
                    sub_data = data
                    break
            except CrunchyrollError:
                continue

        return CrunchyrollSubscription.from_dict(sub_data, benefits=token_benefits)

    async def get_watchlist(self, limit: int = 50) -> list[CrunchyrollItem]:
        if not self.account_id:
            await self.get_profile()
        data = await self.request(
            "GET",
            f"content/v2/discover/{self.account_id}/watchlist",
            params={"locale": self.locale, "n": limit},
        )
        items = data.get("data", [])
        return [CrunchyrollItem.from_panel_dict(it) for it in items]

    async def get_watch_history_with_total(
        self, limit: int = 20, page: int = 1
    ) -> tuple[list[CrunchyrollItem], int]:
        if not self.account_id:
            await self.get_profile()
        data = await self.request(
            "GET",
            f"content/v2/{self.account_id}/watch-history",
            params={"page_size": limit, "page": page, "locale": self.locale},
        )
        items = data.get("data", [])
        total = int(data.get("total", len(items)))
        return [CrunchyrollItem.from_panel_dict(it) for it in items], total

    async def get_watch_history(
        self, limit: int = 20, page: int = 1
    ) -> list[CrunchyrollItem]:
        items, _ = await self.get_watch_history_with_total(limit=limit, page=page)
        return items

    async def get_continue_watching(self, limit: int = 100) -> list[CrunchyrollItem]:
        """Fetch native continue watching list."""
        if not self.account_id:
            await self.get_profile()
        data = await self.request(
            "GET",
            f"content/v2/discover/{self.account_id}/history",
            params={"locale": self.locale, "n": limit},
        )
        items = data.get("data", [])
        return [CrunchyrollItem.from_panel_dict(it) for it in items]

    async def get_recommendations(self, limit: int = 20) -> list[CrunchyrollItem]:
        if not self.account_id:
            await self.get_profile()
        data = await self.request(
            "GET",
            f"content/v2/discover/{self.account_id}/recommendations",
            params={"n": limit, "locale": self.locale},
        )
        items = data.get("data", [])
        return [CrunchyrollItem.from_panel_dict(it) for it in items]

    async def search(self, query: str, limit: int = 10) -> list[CrunchyrollItem]:
        data = await self.request(
            "GET",
            "content/v2/discover/search",
            params={"q": query, "n": limit, "locale": self.locale},
        )
        results: list[CrunchyrollItem] = []
        data_blocks = data.get("data", [])
        for block in data_blocks:
            for it in block.get("items", []):
                results.append(CrunchyrollItem.from_panel_dict(it))
        return results

    async def add_to_watchlist(self, content_id: str) -> bool:
        """Add a series or movie to user watchlist."""
        if not self.account_id:
            await self.get_profile()
        await self.request(
            "POST",
            f"content/v2/{self.account_id}/watchlist",
            json_data={"content_id": content_id},
        )
        return True

    async def remove_from_watchlist(self, content_id: str) -> bool:
        """Remove a series or movie from user watchlist."""
        if not self.account_id:
            await self.get_profile()
        await self.request(
            "DELETE",
            f"content/v2/{self.account_id}/watchlist/{content_id}",
        )
        return True

    async def get_new_animes(self, limit: int = 15) -> list[CrunchyrollItem]:
        """Fetch newly added anime releases."""
        try:
            data = await self.request(
                "GET",
                "content/v2/discover/browse",
                params={"sort_by": "newly_added", "n": limit, "locale": self.locale},
            )
            items = data.get("data", [])
            return [CrunchyrollItem.from_panel_dict(it) for it in items]
        except CrunchyrollError as err:
            _LOGGER.warning("Failed to fetch new anime releases: %s", err)
            return []

    async def get_popular_animes(self, limit: int = 25) -> list[CrunchyrollItem]:
        """Fetch popular / trending anime."""
        try:
            data = await self.request(
                "GET",
                "content/v2/discover/browse",
                params={"sort_by": "popularity", "n": limit, "locale": self.locale},
            )
            items = data.get("data", [])
            return [CrunchyrollItem.from_panel_dict(it) for it in items]
        except CrunchyrollError as err:
            _LOGGER.warning("Failed to fetch popular anime: %s", err)
            return []

    async def get_custom_lists(self) -> list[CustomList]:
        """Fetch user custom lists / crunchylists."""
        if not self.account_id:
            await self.get_profile()
        try:
            data = await self.request(
                "GET", f"content/v2/{self.account_id}/custom-lists"
            )
            items = data.get("data", [])
            return [
                CustomList(
                    list_id=it.get("list_id", ""),
                    title=it.get("title", ""),
                    total=it.get("total", 0),
                    is_public=it.get("is_public", False),
                    modified_at=it.get("modified_at", ""),
                )
                for it in items
            ]
        except CrunchyrollError as err:
            _LOGGER.warning("Failed to fetch custom lists: %s", err)
            return []

    async def get_custom_list_items(self, list_id: str) -> list[CrunchyrollItem]:
        """Fetch items in a specific custom list."""
        if not self.account_id:
            await self.get_profile()
        try:
            data = await self.request(
                "GET", f"content/v2/{self.account_id}/custom-lists/{list_id}"
            )
            items = data.get("data", [])
            return [CrunchyrollItem.from_panel_dict(it) for it in items]
        except CrunchyrollError as err:
            _LOGGER.warning(
                "Failed to fetch custom list items for %s: %s", list_id, err
            )
            return []

    async def get_categories(self) -> list[Category]:
        """Fetch anime categories / genres."""
        try:
            data = await self.request("GET", "content/v2/discover/categories")
            items = data.get("data", [])
            return [
                Category(
                    id=it.get("id", ""),
                    localization=it.get("localization", {}).get("title", ""),
                )
                for it in items
            ]
        except CrunchyrollError as err:
            _LOGGER.warning("Failed to fetch categories: %s", err)
            return []

    async def get_similar(
        self, series_id: str, limit: int = 10
    ) -> list[CrunchyrollItem]:
        """Fetch similar series for a given anime."""
        if not self.account_id:
            await self.get_profile()
        try:
            data = await self.request(
                "GET",
                f"content/v2/discover/{self.account_id}/similar_to/{series_id}",
                params={"n": limit, "locale": self.locale},
            )
            items = data.get("data", [])
            return [CrunchyrollItem.from_panel_dict(it) for it in items]
        except CrunchyrollError as err:
            _LOGGER.warning("Failed to fetch similar anime for %s: %s", series_id, err)
            return []

    async def get_series_seasons(self, series_id: str) -> list[dict[str, Any]]:
        """Fetch seasons for an anime series."""
        try:
            data = await self.request(
                "GET",
                f"content/v2/cms/series/{series_id}/seasons",
                params={"locale": self.locale},
            )
            return data.get("data", [])
        except CrunchyrollError as err:
            _LOGGER.warning("Failed to fetch seasons for %s: %s", series_id, err)
            return []

    async def get_season_episodes(self, season_id: str) -> list[dict[str, Any]]:
        """Fetch all episodes for a specific season."""
        try:
            data = await self.request(
                "GET",
                f"content/v2/cms/seasons/{season_id}/episodes",
                params={"locale": self.locale},
            )
            return data.get("data", [])
        except CrunchyrollError as err:
            _LOGGER.warning("Failed to fetch episodes for %s: %s", season_id, err)
            return []

    async def get_simulcasts(self, limit: int = 25) -> list[CrunchyrollItem]:
        """Fetch active simulcast season releases."""
        try:
            data = await self.request(
                "GET",
                "content/v2/discover/browse",
                params={
                    "browse_type": "simulcasts",
                    "locale": self.locale,
                    "n": limit,
                },
            )
            items = data.get("data", [])
            return [CrunchyrollItem.from_panel_dict(it) for it in items]
        except CrunchyrollError as err:
            _LOGGER.warning("Failed to fetch simulcasts: %s", err)
            return []

    async def get_movies(self, limit: int = 25) -> list[CrunchyrollItem]:
        """Fetch anime movies."""
        try:
            data = await self.request(
                "GET",
                "content/v2/discover/browse",
                params={
                    "type": "movie_listing",
                    "locale": self.locale,
                    "n": limit,
                },
            )
            items = data.get("data", [])
            return [CrunchyrollItem.from_panel_dict(it) for it in items]
        except CrunchyrollError as err:
            _LOGGER.warning("Failed to fetch movies: %s", err)
            return []

    async def get_new_episodes(self, limit: int = 50) -> list[CrunchyrollItem]:
        """Fetch newly added episodes / releases."""
        try:
            data = await self.request(
                "GET",
                "content/v2/discover/browse",
                params={
                    "type": "episode",
                    "sort_by": "newly_added",
                    "locale": self.locale,
                    "n": limit,
                },
            )
            items = data.get("data", [])
            return [CrunchyrollItem.from_panel_dict(it) for it in items]
        except CrunchyrollError as err:
            _LOGGER.warning("Failed to fetch new episodes: %s", err)
            return []

    async def get_up_next(self, series_id: str) -> dict[str, Any]:
        """Fetch up next episode for a specific series."""
        try:
            data = await self.request(
                "GET",
                f"content/v2/discover/up_next/{series_id}",
                params={"locale": self.locale},
            )
            items = data.get("data", [])
            return items[0] if items else {}
        except CrunchyrollError as err:
            _LOGGER.warning("Failed to fetch up-next for %s: %s", series_id, err)
            return {}

    async def get_series_details(self, series_id: str) -> dict[str, Any]:
        """Fetch complete series metadata by series ID."""
        try:
            data = await self.request(
                "GET",
                f"content/v2/cms/series/{series_id}",
                params={"locale": self.locale},
            )
            items = data.get("data", [])
            return items[0] if items else {}
        except CrunchyrollError as err:
            _LOGGER.warning("Failed to fetch series details for %s: %s", series_id, err)
            return {}

    async def get_cms_objects(self, object_ids: list[str]) -> list[dict[str, Any]]:
        """Fetch batch objects (series/episodes/movies) by IDs."""
        if not object_ids:
            return []
        try:
            ids_param = ",".join(object_ids)
            data = await self.request(
                "GET",
                f"content/v2/cms/objects/{ids_param}",
                params={"locale": self.locale},
            )
            return data.get("data", [])
        except CrunchyrollError as err:
            _LOGGER.warning("Failed to batch fetch cms objects: %s", err)
            return []

    async def get_seasons(self, series_id: str) -> list[dict[str, Any]]:
        """Fetch all seasons for a series."""
        return await self.get_series_seasons(series_id)

    async def update_playhead(self, content_id: str, playhead_seconds: int) -> bool:
        """Update playback progress / resume position for an episode."""
        if not self.account_id:
            await self.get_profile()
        await self.request(
            "POST",
            f"content/v2/{self.account_id}/playheads",
            json_data={"content_id": content_id, "playhead": playhead_seconds},
        )
        return True

    async def mark_as_watched(self, content_id: str) -> bool:
        """Mark an episode or series as watched."""
        if not self.account_id:
            await self.get_profile()
        await self.request(
            "POST",
            f"content/v2/{self.account_id}/mark_as_watched/{content_id}",
        )
        return True

    async def fetch_all_data(self) -> CrunchyrollData:
        profile = await self.get_profile()
        sub = await self.get_subscription()
        watchlist = await self.get_watchlist(100)
        # Fetch full watch history (up to 10,000 items / 20 pages of 500) so older series are never dropped
        history: list[CrunchyrollItem] = []
        total_history_count = 0
        for page_idx in range(1, 21):
            page_items, total_count = await self.get_watch_history_with_total(
                500, page=page_idx
            )
            if page_idx == 1:
                total_history_count = total_count
            if not page_items:
                break
            history.extend(page_items)
            if len(page_items) < 500:
                break

        if not total_history_count:
            total_history_count = len(history)

        continue_watching = await self.get_continue_watching(100)
        recommendations = await self.get_recommendations(25)
        new_animes = await self.get_new_animes(25)
        popular_animes = await self.get_popular_animes(25)
        simulcasts = await self.get_simulcasts(25)
        movies = await self.get_movies(25)
        new_episodes = await self.get_new_episodes(50)
        custom_lists = await self.get_custom_lists()
        categories = await self.get_categories()

        # Count total watched episodes per series across full history
        series_watched_count: dict[str, int] = {}
        history_series_map: dict[str, CrunchyrollItem] = {}
        for item in history:
            s_id = item.series_id or item.id
            if not s_id:
                continue
            series_watched_count[s_id] = series_watched_count.get(s_id, 0) + 1
            if s_id not in history_series_map:
                history_series_map[s_id] = item

        # In-progress series from native Continue Watching
        in_progress_animes: list[AnimeProgress] = []
        cw_series_ids: set[str] = set()

        for item in continue_watching:
            s_id = item.series_id or item.id
            if not s_id:
                continue
            cw_series_ids.add(s_id)
            s_title = item.series_title or item.title
            watched_count = series_watched_count.get(s_id, 1)

            in_progress_animes.append(
                AnimeProgress(
                    series_id=s_id,
                    series_title=s_title,
                    episode_id=item.id,
                    episode_title=item.title,
                    episode_number=item.episode_number,
                    season_number=item.season_number,
                    season_title=item.season_title,
                    playhead_seconds=item.last_playhead_secs,
                    duration_ms=item.duration_ms,
                    is_completed=False,
                    date_played=item.date_played,
                    image_url=item.image_url,
                    description=item.description,
                    total_episodes_watched=watched_count,
                )
            )

        # Completed series: series in watch history that are NOT in continue watching
        completed_animes: list[AnimeProgress] = []
        completed_ids_to_resolve: list[str] = [
            s_id for s_id in history_series_map if s_id not in cw_series_ids
        ]

        # Resolve series titles and artwork for completed series using cms/objects
        series_metadata_map: dict[str, dict[str, Any]] = {}
        if completed_ids_to_resolve:
            # Resolve in chunks of 20
            for i in range(0, len(completed_ids_to_resolve), 20):
                chunk = completed_ids_to_resolve[i : i + 20]
                cms_objs = await self.get_cms_objects(chunk)
                for obj in cms_objs:
                    obj_id = obj.get("id")
                    if obj_id:
                        series_metadata_map[obj_id] = obj

        for s_id in completed_ids_to_resolve:
            item = history_series_map[s_id]
            s_meta = series_metadata_map.get(s_id, {})

            s_title = s_meta.get("title") or item.series_title or item.title or s_id
            desc = s_meta.get("description") or item.description
            images = s_meta.get("images", {})
            img_url = item.image_url
            if "poster_tall" in images:
                posters = images["poster_tall"]
                if posters and isinstance(posters, list):
                    last_elem = posters[-1]
                    if isinstance(last_elem, list) and last_elem:
                        img_url = last_elem[-1].get("source", img_url)
                    elif isinstance(last_elem, dict):
                        img_url = last_elem.get("source", img_url)

            watched_count = series_watched_count.get(s_id, 1)
            completed_animes.append(
                AnimeProgress(
                    series_id=s_id,
                    series_title=s_title,
                    episode_id=item.id,
                    episode_title=item.title or "Completed",
                    episode_number=item.episode_number,
                    season_number=item.season_number,
                    season_title=item.season_title,
                    playhead_seconds=item.last_playhead_secs,
                    duration_ms=item.duration_ms,
                    is_completed=True,
                    date_played=item.date_played,
                    image_url=img_url,
                    description=desc,
                    total_episodes_watched=watched_count,
                )
            )

        # Filter new episodes belonging to user's watched series or watchlist
        user_series_ids: set[str] = {
            it.series_id or it.id for it in watchlist if it.series_id or it.id
        }
        user_series_ids.update(
            prog.series_id for prog in in_progress_animes if prog.series_id
        )
        user_series_ids.update(
            prog.series_id for prog in completed_animes if prog.series_id
        )

        watched_episode_ids: set[str] = {h.id for h in history if h.id}
        watched_episode_ids.update(
            prog.episode_id for prog in in_progress_animes if prog.episode_id
        )
        watched_episode_ids.update(
            prog.episode_id for prog in completed_animes if prog.episode_id
        )

        # Collect candidate new episodes for watched series that the user hasn't already watched
        candidate_episodes: list[CrunchyrollItem] = [
            ep
            for ep in new_episodes
            if ep.series_id
            and ep.series_id in user_series_ids
            and ep.id not in watched_episode_ids
        ]

        # If user has a preferred audio language, prioritize matching audio dubs
        pref_audio = self.preferred_audio_language
        if pref_audio:
            has_pref_match = any(
                ep.audio_locale == pref_audio
                for ep in candidate_episodes
                if ep.audio_locale
            )
            if has_pref_match:
                candidate_episodes = [
                    ep
                    for ep in candidate_episodes
                    if not ep.audio_locale or ep.audio_locale == pref_audio
                ]

        # Deduplicate multiple dubs / duplicate releases of the exact same episode
        seen_ep_keys: set[tuple[str, str | None]] = set()
        new_episodes_for_watched: list[CrunchyrollItem] = []
        for ep in candidate_episodes:
            ep_key = (ep.series_id or "", ep.episode_number or ep.title)
            if ep_key in seen_ep_keys:
                continue
            seen_ep_keys.add(ep_key)
            new_episodes_for_watched.append(ep)

        return CrunchyrollData(
            profile=profile,
            subscription=sub,
            watchlist=watchlist,
            history=history[:50],
            recommendations=recommendations,
            completed_animes=completed_animes,
            in_progress_animes=in_progress_animes,
            new_animes=new_animes,
            popular_animes=popular_animes,
            simulcasts=simulcasts,
            movies=movies,
            custom_lists=custom_lists,
            categories=categories,
            new_episodes=new_episodes,
            new_episodes_for_watched=new_episodes_for_watched,
            total_history_count=total_history_count,
        )
