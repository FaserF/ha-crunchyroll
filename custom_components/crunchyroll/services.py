from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse

from .const import DOMAIN
from .coordinator import CrunchyrollDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_SEARCH = "search"
SERVICE_GET_WATCHLIST = "get_watchlist"
SERVICE_GET_HISTORY = "get_history"
SERVICE_ADD_TO_WATCHLIST = "add_to_watchlist"
SERVICE_REMOVE_FROM_WATCHLIST = "remove_from_watchlist"
SERVICE_GET_SIMILAR = "get_similar"
SERVICE_GET_SEASONS = "get_seasons"
SERVICE_GET_EPISODES = "get_episodes"
SERVICE_GET_POPULAR = "get_popular"
SERVICE_GET_SIMULCASTS = "get_simulcasts"
SERVICE_GET_MOVIES = "get_movies"
SERVICE_GET_UP_NEXT = "get_up_next"
SERVICE_GET_SERIES_DETAILS = "get_series_details"
SERVICE_GET_CUSTOM_LIST_ITEMS = "get_custom_list_items"
SERVICE_MARK_AS_WATCHED = "mark_as_watched"
SERVICE_UPDATE_PLAYHEAD = "update_playhead"

SEARCH_SCHEMA = vol.Schema(
    {
        vol.Required("query"): cv.string,
        vol.Optional("limit", default=10): cv.positive_int,
    }
)

LIMIT_SCHEMA = vol.Schema(
    {
        vol.Optional("limit", default=20): cv.positive_int,
    }
)

WATCHLIST_ACTION_SCHEMA = vol.Schema(
    {
        vol.Required("content_id"): cv.string,
    }
)

PLAYHEAD_SCHEMA = vol.Schema(
    {
        vol.Required("content_id"): cv.string,
        vol.Required("playhead_seconds"): cv.positive_int,
    }
)

SERIES_ACTION_SCHEMA = vol.Schema(
    {
        vol.Required("series_id"): cv.string,
        vol.Optional("limit", default=10): cv.positive_int,
    }
)

SERIES_ID_SCHEMA = vol.Schema(
    {
        vol.Required("series_id"): cv.string,
    }
)

SEASON_ACTION_SCHEMA = vol.Schema(
    {
        vol.Required("season_id"): cv.string,
    }
)

CUSTOM_LIST_ACTION_SCHEMA = vol.Schema(
    {
        vol.Required("list_id"): cv.string,
    }
)


def _get_first_coordinator(hass: HomeAssistant) -> CrunchyrollDataUpdateCoordinator:
    """Get the first active Crunchyroll coordinator."""
    coordinators = list(hass.data.get(DOMAIN, {}).values())
    if not coordinators:
        raise ValueError("No active Crunchyroll integration found")
    return coordinators[0]


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register Crunchyroll integration services."""

    async def handle_search(call: ServiceCall) -> dict[str, Any]:
        """Handle searching Crunchyroll library."""
        coordinator = _get_first_coordinator(hass)
        query = call.data["query"]
        limit = call.data.get("limit", 10)
        items = await coordinator.client.search(query=query, limit=limit)
        return {
            "results": [
                {
                    "id": it.id,
                    "title": it.title,
                    "type": it.type,
                    "image_url": it.image_url,
                    "description": it.description,
                }
                for it in items
            ]
        }

    async def handle_get_watchlist(call: ServiceCall) -> dict[str, Any]:
        """Handle retrieving watchlist items."""
        coordinator = _get_first_coordinator(hass)
        limit = call.data.get("limit", 20)
        items = await coordinator.client.get_watchlist(limit=limit)
        return {
            "watchlist": [
                {
                    "id": it.id,
                    "title": it.title,
                    "type": it.type,
                    "image_url": it.image_url,
                    "description": it.description,
                }
                for it in items
            ]
        }

    async def handle_get_history(call: ServiceCall) -> dict[str, Any]:
        """Handle retrieving watch history items."""
        coordinator = _get_first_coordinator(hass)
        limit = call.data.get("limit", 20)
        items = await coordinator.client.get_watch_history(limit=limit)
        return {
            "history": [
                {
                    "id": it.id,
                    "title": it.title,
                    "display_title": it.display_title,
                    "series_id": it.series_id,
                    "series_title": it.series_title,
                    "episode_number": it.episode_number,
                    "season_number": it.season_number,
                    "season_title": it.season_title,
                    "image_url": it.image_url,
                    "playhead_seconds": it.last_playhead_secs,
                    "duration_ms": it.duration_ms,
                    "is_completed": it.is_completed,
                    "date_played": it.date_played,
                }
                for it in items
            ]
        }

    async def handle_add_to_watchlist(call: ServiceCall) -> dict[str, Any]:
        """Handle adding anime to user watchlist."""
        coordinator = _get_first_coordinator(hass)
        content_id = call.data["content_id"]
        success = await coordinator.client.add_to_watchlist(content_id)
        await coordinator.async_request_refresh()
        return {"success": success, "content_id": content_id}

    async def handle_remove_from_watchlist(call: ServiceCall) -> dict[str, Any]:
        """Handle removing anime from user watchlist."""
        coordinator = _get_first_coordinator(hass)
        content_id = call.data["content_id"]
        success = await coordinator.client.remove_from_watchlist(content_id)
        await coordinator.async_request_refresh()
        return {"success": success, "content_id": content_id}

    async def handle_get_similar(call: ServiceCall) -> dict[str, Any]:
        """Handle retrieving similar anime."""
        coordinator = _get_first_coordinator(hass)
        series_id = call.data["series_id"]
        limit = call.data.get("limit", 10)
        items = await coordinator.client.get_similar(series_id=series_id, limit=limit)
        return {"similar": [it.to_dict() for it in items]}

    async def handle_get_seasons(call: ServiceCall) -> dict[str, Any]:
        """Handle retrieving seasons of a series."""
        coordinator = _get_first_coordinator(hass)
        series_id = call.data["series_id"]
        seasons = await coordinator.client.get_seasons(series_id=series_id)
        return {"seasons": seasons}

    async def handle_get_episodes(call: ServiceCall) -> dict[str, Any]:
        """Handle retrieving episodes of a season."""
        coordinator = _get_first_coordinator(hass)
        season_id = call.data["season_id"]
        episodes = await coordinator.client.get_season_episodes(season_id=season_id)
        return {"episodes": episodes}

    async def handle_get_popular(call: ServiceCall) -> dict[str, Any]:
        """Handle retrieving popular anime."""
        coordinator = _get_first_coordinator(hass)
        limit = call.data.get("limit", 20)
        items = await coordinator.client.get_popular_animes(limit=limit)
        return {"popular": [it.to_dict() for it in items]}

    async def handle_get_simulcasts(call: ServiceCall) -> dict[str, Any]:
        """Handle retrieving simulcast anime."""
        coordinator = _get_first_coordinator(hass)
        limit = call.data.get("limit", 20)
        items = await coordinator.client.get_simulcasts(limit=limit)
        return {"simulcasts": [it.to_dict() for it in items]}

    async def handle_get_movies(call: ServiceCall) -> dict[str, Any]:
        """Handle retrieving anime movies."""
        coordinator = _get_first_coordinator(hass)
        limit = call.data.get("limit", 20)
        items = await coordinator.client.get_movies(limit=limit)
        return {"movies": [it.to_dict() for it in items]}

    async def handle_get_up_next(call: ServiceCall) -> dict[str, Any]:
        """Handle retrieving up-next episode for a series."""
        coordinator = _get_first_coordinator(hass)
        series_id = call.data["series_id"]
        result = await coordinator.client.get_up_next(series_id=series_id)
        return {"up_next": result}

    async def handle_get_series_details(call: ServiceCall) -> dict[str, Any]:
        """Handle retrieving series metadata details."""
        coordinator = _get_first_coordinator(hass)
        series_id = call.data["series_id"]
        result = await coordinator.client.get_series_details(series_id=series_id)
        return {"series": result}

    async def handle_get_custom_list_items(call: ServiceCall) -> dict[str, Any]:
        """Handle retrieving items of a custom list."""
        coordinator = _get_first_coordinator(hass)
        list_id = call.data["list_id"]
        items = await coordinator.client.get_custom_list_items(list_id=list_id)
        return {"items": [it.to_dict() for it in items]}

    async def handle_update_playhead(call: ServiceCall) -> dict[str, Any]:
        """Handle updating playback progress position."""
        coordinator = _get_first_coordinator(hass)
        content_id = call.data["content_id"]
        playhead_seconds = call.data["playhead_seconds"]
        success = await coordinator.client.update_playhead(
            content_id=content_id, playhead_seconds=playhead_seconds
        )
        return {
            "success": success,
            "content_id": content_id,
            "playhead": playhead_seconds,
        }

    async def handle_mark_as_watched(call: ServiceCall) -> dict[str, Any]:
        """Handle marking episode or series as watched."""
        coordinator = _get_first_coordinator(hass)
        content_id = call.data["content_id"]
        success = await coordinator.client.mark_as_watched(content_id=content_id)
        await coordinator.async_request_refresh()
        return {"success": success, "content_id": content_id}

    if not hass.services.has_service(DOMAIN, SERVICE_SEARCH):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SEARCH,
            handle_search,
            schema=SEARCH_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_GET_WATCHLIST):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_WATCHLIST,
            handle_get_watchlist,
            schema=LIMIT_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_GET_HISTORY):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_HISTORY,
            handle_get_history,
            schema=LIMIT_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_ADD_TO_WATCHLIST):
        hass.services.async_register(
            DOMAIN,
            SERVICE_ADD_TO_WATCHLIST,
            handle_add_to_watchlist,
            schema=WATCHLIST_ACTION_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_REMOVE_FROM_WATCHLIST):
        hass.services.async_register(
            DOMAIN,
            SERVICE_REMOVE_FROM_WATCHLIST,
            handle_remove_from_watchlist,
            schema=WATCHLIST_ACTION_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_GET_SIMILAR):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_SIMILAR,
            handle_get_similar,
            schema=SERIES_ACTION_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_GET_SEASONS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_SEASONS,
            handle_get_seasons,
            schema=SERIES_ACTION_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_GET_EPISODES):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_EPISODES,
            handle_get_episodes,
            schema=SEASON_ACTION_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_GET_POPULAR):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_POPULAR,
            handle_get_popular,
            schema=LIMIT_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_GET_SIMULCASTS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_SIMULCASTS,
            handle_get_simulcasts,
            schema=LIMIT_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_GET_MOVIES):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_MOVIES,
            handle_get_movies,
            schema=LIMIT_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_GET_UP_NEXT):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_UP_NEXT,
            handle_get_up_next,
            schema=SERIES_ID_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_GET_SERIES_DETAILS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_SERIES_DETAILS,
            handle_get_series_details,
            schema=SERIES_ID_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_GET_CUSTOM_LIST_ITEMS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_GET_CUSTOM_LIST_ITEMS,
            handle_get_custom_list_items,
            schema=CUSTOM_LIST_ACTION_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_UPDATE_PLAYHEAD):
        hass.services.async_register(
            DOMAIN,
            SERVICE_UPDATE_PLAYHEAD,
            handle_update_playhead,
            schema=PLAYHEAD_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_MARK_AS_WATCHED):
        hass.services.async_register(
            DOMAIN,
            SERVICE_MARK_AS_WATCHED,
            handle_mark_as_watched,
            schema=WATCHLIST_ACTION_SCHEMA,
            supports_response=SupportsResponse.OPTIONAL,
        )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister Crunchyroll services."""
    for service in (
        SERVICE_SEARCH,
        SERVICE_GET_WATCHLIST,
        SERVICE_GET_HISTORY,
        SERVICE_ADD_TO_WATCHLIST,
        SERVICE_REMOVE_FROM_WATCHLIST,
        SERVICE_GET_SIMILAR,
        SERVICE_GET_SEASONS,
        SERVICE_GET_EPISODES,
        SERVICE_GET_POPULAR,
        SERVICE_GET_SIMULCASTS,
        SERVICE_GET_MOVIES,
        SERVICE_GET_UP_NEXT,
        SERVICE_GET_SERIES_DETAILS,
        SERVICE_GET_CUSTOM_LIST_ITEMS,
        SERVICE_UPDATE_PLAYHEAD,
        SERVICE_MARK_AS_WATCHED,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
