from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crunchyroll.api.exceptions import (
    AuthenticationError,
    ConnectionError,
)
from custom_components.crunchyroll.const import CONF_EMAIL, CONF_PASSWORD, DOMAIN
from custom_components.crunchyroll.coordinator import CrunchyrollDataUpdateCoordinator


async def test_coordinator_update_success(
    hass: HomeAssistant, mock_crunchyroll_client, mock_crunchyroll_data
) -> None:
    """Test successful coordinator update."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_EMAIL: "u", CONF_PASSWORD: "p"})
    entry.add_to_hass(hass)
    coordinator = CrunchyrollDataUpdateCoordinator(
        hass, mock_crunchyroll_client, config_entry=entry, update_interval_seconds=300
    )
    await coordinator.async_refresh()
    assert coordinator.last_update_success is True
    assert coordinator.data.profile.username == "anime_hero"
    assert coordinator.data.subscription.is_premium is True
    assert len(coordinator.data.watchlist) == 1


async def test_coordinator_update_auth_failed(
    hass: HomeAssistant, mock_crunchyroll_client
) -> None:
    """Test coordinator raises ConfigEntryAuthFailed on AuthenticationError."""
    mock_crunchyroll_client.fetch_all_data.side_effect = AuthenticationError(
        "Auth expired"
    )
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_EMAIL: "u", CONF_PASSWORD: "p"})
    entry.add_to_hass(hass)
    coordinator = CrunchyrollDataUpdateCoordinator(
        hass, mock_crunchyroll_client, config_entry=entry, update_interval_seconds=300
    )
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_coordinator_update_connection_error(
    hass: HomeAssistant, mock_crunchyroll_client
) -> None:
    """Test coordinator raises UpdateFailed on ConnectionError."""
    mock_crunchyroll_client.fetch_all_data.side_effect = ConnectionError("Offline")
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_EMAIL: "u", CONF_PASSWORD: "p"})
    entry.add_to_hass(hass)
    coordinator = CrunchyrollDataUpdateCoordinator(
        hass, mock_crunchyroll_client, config_entry=entry, update_interval_seconds=300
    )
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_new_episode_event(
    hass: HomeAssistant, mock_crunchyroll_client, mock_crunchyroll_data
) -> None:
    """Test coordinator fires crunchyroll_new_episode_available event."""
    from custom_components.crunchyroll.const import (
        EVENT_CRUNCHYROLL_NEW_EPISODE_AVAILABLE,
    )

    events: list[dict] = []

    def handle_event(event):
        events.append(event.data)

    hass.bus.async_listen(EVENT_CRUNCHYROLL_NEW_EPISODE_AVAILABLE, handle_event)

    entry = MockConfigEntry(domain=DOMAIN, data={CONF_EMAIL: "u", CONF_PASSWORD: "p"})
    entry.add_to_hass(hass)
    coordinator = CrunchyrollDataUpdateCoordinator(
        hass, mock_crunchyroll_client, config_entry=entry, update_interval_seconds=300
    )

    # First update sets baseline
    await coordinator._async_update_data()
    assert len(events) == 0

    # Second update with a newly released episode for watched series
    from custom_components.crunchyroll.api.models import CrunchyrollItem

    new_ep = CrunchyrollItem(
        id="ep-new-1",
        title="The Next Chapter",
        series_id="series-001",
        series_title="Frieren: Beyond Journey's End",
        episode_number="29",
        season_number=2,
        release_date="2026-09-05T12:00:00Z",
    )
    mock_crunchyroll_data.new_episodes_for_watched = [
        mock_crunchyroll_data.new_episodes_for_watched[0],
        new_ep,
    ]

    await coordinator._async_update_data()
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0]["episode_id"] == "ep-new-1"
    assert events[0]["series_title"] == "Frieren: Beyond Journey's End"
    assert events[0]["episode_number"] == "29"
