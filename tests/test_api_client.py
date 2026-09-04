from __future__ import annotations

import httpx
import pytest

from custom_components.crunchyroll.api.client import CrunchyrollClient
from custom_components.crunchyroll.api.exceptions import (
    AuthenticationError,
)


@pytest.mark.asyncio
async def test_client_login_success() -> None:
    """Test successful client login and token parsing."""

    def handler(request: httpx.Request) -> httpx.Response:
        if "auth/v1/token" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "access_token": "fake_access_token_123",
                    "refresh_token": "fake_refresh_token_456",
                    "expires_in": 3600,
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = CrunchyrollClient(
            email="user@test.com",
            password="password",
            http_client=http_client,
        )
        assert await client.login() is True
        assert client.is_authorized is True
        assert client.access_token == "fake_access_token_123"


@pytest.mark.asyncio
async def test_client_login_invalid_auth() -> None:
    """Test client login with invalid credentials."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_grant"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = CrunchyrollClient(
            email="user@test.com",
            password="wrong",
            http_client=http_client,
        )
        with pytest.raises(AuthenticationError):
            await client.login()


@pytest.mark.asyncio
async def test_client_fetch_watchlist() -> None:
    """Test fetching watchlist items."""

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "auth/v1/token" in url_str:
            return httpx.Response(
                200,
                json={
                    "access_token": "tok",
                    "refresh_token": "ref",
                    "expires_in": 3600,
                },
            )
        if "accounts/v1/me/profile" in url_str:
            return httpx.Response(
                200,
                json={"account_id": "acc-999", "profile_name": "ProWatcher"},
            )
        if "watchlist" in url_str:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "series-123",
                            "type": "series",
                            "panel": {
                                "id": "series-123",
                                "title": "Attack on Titan",
                                "description": "Epic anime",
                                "images": {
                                    "poster_tall": [{"source": "http://img.jpg"}]
                                },
                            },
                        }
                    ]
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = CrunchyrollClient(
            email="user@test.com",
            password="pw",
            http_client=http_client,
        )
        watchlist = await client.get_watchlist(10)
        assert len(watchlist) == 1
        assert watchlist[0].title == "Attack on Titan"
        assert watchlist[0].image_url == "http://img.jpg"


@pytest.mark.asyncio
async def test_client_fetch_continue_watching() -> None:
    """Test fetching continue watching items."""

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "auth/v1/token" in url_str:
            return httpx.Response(
                200,
                json={
                    "access_token": "tok",
                    "refresh_token": "ref",
                    "expires_in": 3600,
                },
            )
        if "content/v2/discover" in url_str and "history" in url_str:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "ep-123",
                            "type": "episode",
                            "panel": {
                                "id": "ep-123",
                                "title": "Clash",
                                "episode_metadata": {
                                    "series_id": "series-seirei",
                                    "series_title": "Seirei Gensouki: Spirit Chronicles",
                                    "episode_number": "11",
                                    "season_number": 2,
                                    "duration_ms": 1420000,
                                },
                            },
                            "playhead": 350,
                        }
                    ]
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = CrunchyrollClient(
            email="u",
            password="p",
            account_id="acc-1",
            access_token="tok",
            http_client=http_client,
        )
        cw = await client.get_continue_watching(10)
        assert len(cw) == 1
        assert cw[0].series_title == "Seirei Gensouki: Spirit Chronicles"
        assert cw[0].episode_number == "11"
        assert cw[0].last_playhead_secs == 350


@pytest.mark.asyncio
async def test_client_popular_and_custom_lists() -> None:
    """Test fetching popular anime and custom lists."""

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "auth/v1/token" in url_str:
            return httpx.Response(
                200,
                json={
                    "access_token": "tok",
                    "refresh_token": "ref",
                    "expires_in": 3600,
                    "account_id": "acc-1",
                },
            )
        if "content/v2/discover/browse" in url_str:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "s-pop", "title": "Jujutsu Kaisen", "type": "series"}
                    ]
                },
            )
        if "custom-lists" in url_str:
            return httpx.Response(
                200,
                json={
                    "data": [{"list_id": "cl-1", "title": "Top Favorites", "total": 3}]
                },
            )
        if "categories" in url_str:
            return httpx.Response(
                200,
                json={"data": [{"id": "action", "localization": {"title": "Action"}}]},
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = CrunchyrollClient(email="u", password="p", http_client=http_client)
        popular = await client.get_popular_animes(5)
        assert len(popular) == 1
        assert popular[0].title == "Jujutsu Kaisen"

        lists = await client.get_custom_lists()
        assert len(lists) == 1
        assert lists[0].title == "Top Favorites"

        cats = await client.get_categories()
        assert len(cats) == 1
        assert cats[0].id == "action"


@pytest.mark.asyncio
async def test_client_actions() -> None:
    """Test watchlist and watched action endpoints."""

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "auth/v1/token" in url_str:
            return httpx.Response(
                200,
                json={
                    "access_token": "tok",
                    "refresh_token": "ref",
                    "expires_in": 3600,
                    "account_id": "acc-1",
                },
            )
        if request.method in ("POST", "DELETE"):
            return httpx.Response(204)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = CrunchyrollClient(
            email="u",
            password="p",
            account_id="acc-1",
            access_token="tok",
            http_client=http_client,
        )
        assert await client.add_to_watchlist("s-123") is True
        assert await client.remove_from_watchlist("s-123") is True
        assert await client.mark_as_watched("ep-123") is True


@pytest.mark.asyncio
async def test_client_simulcasts_movies_and_details() -> None:
    """Test fetching simulcasts, movies, up next, and series details."""

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "auth/v1/token" in url_str:
            return httpx.Response(
                200,
                json={
                    "access_token": "tok",
                    "refresh_token": "ref",
                    "expires_in": 3600,
                },
            )
        if "browse_type=simulcasts" in url_str:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "sim-1", "title": "Winter Simulcast", "type": "series"}
                    ]
                },
            )
        if "type=movie_listing" in url_str:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "mov-1", "title": "Anime Movie", "type": "movie_listing"}
                    ]
                },
            )
        if "discover/up_next" in url_str:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "ep-next", "title": "Next Episode", "type": "episode"}
                    ]
                },
            )
        if "cms/series/s-100/seasons" in url_str:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "season-1",
                            "title": "Season 1",
                            "number_of_episodes": 12,
                        }
                    ]
                },
            )
        if "cms/series/s-100" in url_str:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "s-100",
                            "title": "Hero Academia",
                            "episode_count": 138,
                            "season_count": 7,
                        }
                    ]
                },
            )
        if "type=episode" in url_str and "sort_by=newly_added" in url_str:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "ep-new",
                            "type": "episode",
                            "panel": {
                                "id": "ep-new",
                                "title": "New Release Episode",
                                "episode_metadata": {
                                    "series_id": "s-100",
                                    "series_title": "Hero Academia",
                                    "episode_number": 139,
                                    "availability_starts": "2026-09-04T12:00:00Z",
                                },
                            },
                        }
                    ]
                },
            )
        if "cms/seasons/season-1/episodes" in url_str:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "ep-101", "title": "Episode 1", "sequence_number": 1}
                    ]
                },
            )
        if "similar_to/s-100" in url_str:
            return httpx.Response(
                200,
                json={"data": [{"id": "sim-1", "panel": {"title": "Similar Anime"}}]},
            )
        if "custom-lists/cl-1" in url_str:
            return httpx.Response(
                200,
                json={"data": [{"id": "item-cl-1", "panel": {"title": "List Anime"}}]},
            )
        if "playheads" in url_str:
            return httpx.Response(200, json={})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = CrunchyrollClient(
            email="u",
            password="p",
            account_id="acc-1",
            access_token="tok",
            http_client=http_client,
        )
        simulcasts = await client.get_simulcasts(5)
        assert len(simulcasts) == 1
        assert simulcasts[0].title == "Winter Simulcast"

        movies = await client.get_movies(5)
        assert len(movies) == 1
        assert movies[0].title == "Anime Movie"

        new_eps = await client.get_new_episodes(5)
        assert len(new_eps) == 1
        assert new_eps[0].title == "New Release Episode"
        assert new_eps[0].release_date == "2026-09-04T12:00:00Z"

        up_next = await client.get_up_next("s-100")
        assert up_next.get("title") == "Next Episode"

        details = await client.get_series_details("s-100")
        assert details.get("episode_count") == 138

        seasons = await client.get_seasons("s-100")
        assert len(seasons) == 1
        assert seasons[0]["id"] == "season-1"

        episodes = await client.get_season_episodes("season-1")
        assert len(episodes) == 1
        assert episodes[0]["id"] == "ep-101"

        similar = await client.get_similar("s-100", 5)
        assert len(similar) == 1
        assert similar[0].title == "Similar Anime"

        list_items = await client.get_custom_list_items("cl-1")
        assert len(list_items) == 1
        assert list_items[0].title == "List Anime"

        playhead_res = await client.update_playhead("ep-101", 150)
        assert playhead_res is True
