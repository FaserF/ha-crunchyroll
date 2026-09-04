from __future__ import annotations

import os
import socket
from unittest.mock import AsyncMock

import pytest
import pytest_socket

from custom_components.crunchyroll.api.models import (
    AnimeProgress,
    Category,
    CrunchyrollData,
    CrunchyrollItem,
    CrunchyrollProfile,
    CrunchyrollSubscription,
    CustomList,
)

# On Windows Python 3.14, asyncio proactor event loop needs socketpair() for internal self-pipes.
# pytest_runtest_setup in pytest_homeassistant_custom_component calls disable_socket(allow_unix_socket=True),
# which blocks AF_INET socketpair on Windows. We patch disable_socket to allow AF_INET loopback.
_original_disable_socket = pytest_socket.disable_socket


def _custom_disable_socket(allow_unix_socket: bool = False) -> None:
    _original_disable_socket(allow_unix_socket=allow_unix_socket)
    orig_new = socket.socket.__new__

    def _guarded_new(
        cls, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, fileno=None
    ):
        if os.name == "nt" and family == socket.AF_INET and type == socket.SOCK_STREAM:
            return super(socket.socket, cls).__new__(cls, family, type, proto, fileno)
        return orig_new(cls, family, type, proto, fileno)

    socket.socket.__new__ = _guarded_new  # type: ignore[method-assign]


pytest_socket.disable_socket = _custom_disable_socket


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in Home Assistant tests."""
    yield


@pytest.fixture
def mock_profile() -> CrunchyrollProfile:
    """Fixture for Crunchyroll profile."""
    return CrunchyrollProfile(
        account_id="acc-12345",
        profile_name="AnimeHero",
        username="anime_hero",
        email="test@example.com",
        email_verified=True,
        maturity_rating="M3",
        avatar="https://img.crunchyroll.com/avatar.png",
        preferred_communication_language="de-DE",
        preferred_content_subtitle_language="de-DE",
    )


@pytest.fixture
def mock_subscription() -> CrunchyrollSubscription:
    """Fixture for Crunchyroll subscription."""
    return CrunchyrollSubscription(
        is_premium=True,
        tier="mega_fan",
        products=["premium_tier_mega_fan"],
    )


@pytest.fixture
def mock_item() -> CrunchyrollItem:
    """Fixture for Crunchyroll item."""
    return CrunchyrollItem(
        id="item-001",
        title="Frieren: Beyond Journey's End",
        description="An adventure that begins after the demon king is defeated.",
        type="series",
        image_url="https://img.crunchyroll.com/poster.jpg",
        series_id="series-001",
        series_title="Frieren: Beyond Journey's End",
        episode_number="28",
        season_title="Season 1",
        last_playhead_secs=1200,
        duration_ms=1440000,
        is_completed=True,
        release_date="2026-09-04T12:00:00Z",
    )


@pytest.fixture
def mock_progress() -> AnimeProgress:
    """Fixture for anime watch progress."""
    return AnimeProgress(
        series_id="series-001",
        series_title="Frieren: Beyond Journey's End",
        episode_id="item-001",
        episode_title="The Journey's End",
        episode_number="28",
        season_number=1,
        season_title="Season 1",
        playhead_seconds=1200,
        duration_ms=1440000,
        is_completed=True,
    )


@pytest.fixture
def mock_custom_list() -> CustomList:
    """Fixture for user custom list."""
    return CustomList(
        list_id="list-123",
        title="Favorite Shonen",
        total=5,
        is_public=False,
        modified_at="2026-09-01T12:00:00Z",
    )


@pytest.fixture
def mock_category() -> Category:
    """Fixture for category."""
    return Category(id="action", localization="Action")


@pytest.fixture
def mock_crunchyroll_data(
    mock_profile: CrunchyrollProfile,
    mock_subscription: CrunchyrollSubscription,
    mock_item: CrunchyrollItem,
    mock_progress: AnimeProgress,
    mock_custom_list: CustomList,
    mock_category: Category,
) -> CrunchyrollData:
    """Fixture for consolidated Crunchyroll data."""
    return CrunchyrollData(
        profile=mock_profile,
        subscription=mock_subscription,
        watchlist=[mock_item],
        history=[mock_item],
        recommendations=[mock_item],
        completed_animes=[mock_progress],
        in_progress_animes=[mock_progress],
        new_animes=[mock_item],
        popular_animes=[mock_item],
        simulcasts=[mock_item],
        movies=[mock_item],
        custom_lists=[mock_custom_list],
        categories=[mock_category],
        new_episodes=[mock_item],
        new_episodes_for_watched=[mock_item],
    )


@pytest.fixture
def mock_crunchyroll_client(mock_crunchyroll_data: CrunchyrollData):
    """Fixture for mocked CrunchyrollClient."""
    client = AsyncMock()
    client.login = AsyncMock(return_value=True)
    client.close = AsyncMock(return_value=None)
    client.get_profile = AsyncMock(return_value=mock_crunchyroll_data.profile)
    client.get_subscription = AsyncMock(return_value=mock_crunchyroll_data.subscription)
    client.get_watchlist = AsyncMock(return_value=mock_crunchyroll_data.watchlist)
    client.get_watch_history = AsyncMock(return_value=mock_crunchyroll_data.history)
    client.get_continue_watching = AsyncMock(return_value=mock_crunchyroll_data.history)
    client.get_recommendations = AsyncMock(
        return_value=mock_crunchyroll_data.recommendations
    )
    client.get_new_animes = AsyncMock(return_value=mock_crunchyroll_data.new_animes)
    client.get_popular_animes = AsyncMock(
        return_value=mock_crunchyroll_data.popular_animes
    )
    client.get_simulcasts = AsyncMock(return_value=mock_crunchyroll_data.simulcasts)
    client.get_movies = AsyncMock(return_value=mock_crunchyroll_data.movies)
    client.get_new_episodes = AsyncMock(return_value=mock_crunchyroll_data.new_episodes)
    client.get_up_next = AsyncMock(
        return_value={"id": "ep-next", "title": "Next Episode"}
    )
    client.get_series_details = AsyncMock(
        return_value={"id": "series-1", "title": "Series Details"}
    )
    client.get_custom_lists = AsyncMock(return_value=mock_crunchyroll_data.custom_lists)
    client.get_custom_list_items = AsyncMock(
        return_value=mock_crunchyroll_data.watchlist
    )
    client.get_categories = AsyncMock(return_value=mock_crunchyroll_data.categories)
    client.get_similar = AsyncMock(return_value=mock_crunchyroll_data.recommendations)
    client.get_seasons = AsyncMock(
        return_value=[{"id": "season-1", "title": "Season 1"}]
    )
    client.get_season_episodes = AsyncMock(
        return_value=[{"id": "ep-1", "title": "Episode 1"}]
    )
    client.update_playhead = AsyncMock(return_value=True)
    client.add_to_watchlist = AsyncMock(return_value=True)
    client.remove_from_watchlist = AsyncMock(return_value=True)
    client.mark_as_watched = AsyncMock(return_value=True)
    client.search = AsyncMock(return_value=mock_crunchyroll_data.watchlist)
    client.fetch_all_data = AsyncMock(return_value=mock_crunchyroll_data)
    client.is_authorized = True
    return client
