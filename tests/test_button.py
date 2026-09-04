from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crunchyroll.api.models import AnimeProgress, CrunchyrollItem
from custom_components.crunchyroll.const import CONF_EMAIL, CONF_PASSWORD, DOMAIN


async def test_button_setup_and_press(
    hass: HomeAssistant, mock_crunchyroll_client, mock_crunchyroll_data
) -> None:
    """Test clean watchlist button setup and press."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_EMAIL: "test@example.com", CONF_PASSWORD: "secret"},
        entry_id="test_entry_id",
    )
    entry.add_to_hass(hass)

    # Set up completed anime that is also in the watchlist
    mock_item = CrunchyrollItem(
        id="series-1",
        title="Completed Series",
        series_id="series-1",
    )
    mock_crunchyroll_data.watchlist = [mock_item]
    mock_crunchyroll_data.completed_animes = [
        AnimeProgress(
            series_id="series-1",
            series_title="Completed Series",
            episode_id="ep-10",
            episode_title="Final Episode",
            is_completed=True,
        )
    ]

    with patch(
        "custom_components.crunchyroll.CrunchyrollClient",
        return_value=mock_crunchyroll_client,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Find button entity
        buttons = hass.states.async_entity_ids("button")
        assert len(buttons) == 1
        button_id = buttons[0]
        assert "clean_watched_from_watchlist" in button_id

        # Press button
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": button_id},
            blocking=True,
        )
        await hass.async_block_till_done()

        mock_crunchyroll_client.remove_from_watchlist.assert_awaited_once_with(
            "series-1"
        )
        assert len(mock_crunchyroll_data.watchlist) == 0
