from __future__ import annotations

from unittest.mock import patch

from homeassistant.components.media_player import (
    BrowseMedia,
    MediaPlayerState,
    MediaType,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crunchyroll.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    DOMAIN,
)
from custom_components.crunchyroll.media_player import (
    MEDIA_TYPE_CR_CATEGORIES,
    MEDIA_TYPE_CR_CATEGORY,
    MEDIA_TYPE_CR_CONTINUE_WATCHING,
    MEDIA_TYPE_CR_NEW,
    MEDIA_TYPE_CR_POPULAR,
    MEDIA_TYPE_CR_ROOT,
    MEDIA_TYPE_CR_SEASON,
    MEDIA_TYPE_CR_SERIES,
    MEDIA_TYPE_CR_SIMULCASTS,
    MEDIA_TYPE_CR_WATCHLIST,
    CrunchyrollMediaPlayer,
)


async def test_media_player_setup_and_browse(
    hass: HomeAssistant, mock_crunchyroll_client
) -> None:
    """Test media_player setup, media browsing and play media."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_EMAIL: "test@example.com", CONF_PASSWORD: "secret"},
        entry_id="test_entry_id",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.crunchyroll.CrunchyrollClient",
        return_value=mock_crunchyroll_client,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        players = hass.states.async_entity_ids("media_player")
        assert len(players) == 1
        player_id = players[0]
        state = hass.states.get(player_id)
        assert state is not None
        assert state.state == MediaPlayerState.IDLE

        # Test root browse
        coordinator = hass.data[DOMAIN][entry.entry_id]
        player = CrunchyrollMediaPlayer(coordinator, entry)
        player.hass = hass

        root_browse: BrowseMedia = await player.async_browse_media()
        assert root_browse.media_content_type == MEDIA_TYPE_CR_ROOT
        assert len(root_browse.children) == 6

        # Test continue watching browse
        cw_browse = await player.async_browse_media(
            MEDIA_TYPE_CR_CONTINUE_WATCHING, f"{MEDIA_TYPE_CR_CONTINUE_WATCHING}:"
        )
        assert cw_browse.media_content_type == MEDIA_TYPE_CR_CONTINUE_WATCHING
        assert len(cw_browse.children) > 0

        # Test watchlist browse
        wl_browse = await player.async_browse_media(
            MEDIA_TYPE_CR_WATCHLIST, f"{MEDIA_TYPE_CR_WATCHLIST}:"
        )
        assert wl_browse.media_content_type == MEDIA_TYPE_CR_WATCHLIST
        assert len(wl_browse.children) > 0

        # Test simulcasts browse
        sc_browse = await player.async_browse_media(
            MEDIA_TYPE_CR_SIMULCASTS, f"{MEDIA_TYPE_CR_SIMULCASTS}:"
        )
        assert sc_browse.media_content_type == MEDIA_TYPE_CR_SIMULCASTS

        # Test popular browse
        pop_browse = await player.async_browse_media(
            MEDIA_TYPE_CR_POPULAR, f"{MEDIA_TYPE_CR_POPULAR}:"
        )
        assert pop_browse.media_content_type == MEDIA_TYPE_CR_POPULAR

        # Test new browse
        new_browse = await player.async_browse_media(
            MEDIA_TYPE_CR_NEW, f"{MEDIA_TYPE_CR_NEW}:"
        )
        assert new_browse.media_content_type == MEDIA_TYPE_CR_NEW

        # Test categories browse
        cat_browse = await player.async_browse_media(
            MEDIA_TYPE_CR_CATEGORIES, f"{MEDIA_TYPE_CR_CATEGORIES}:"
        )
        assert cat_browse.media_content_type == MEDIA_TYPE_CR_CATEGORIES

        # Test category item browse
        cat_item_browse = await player.async_browse_media(
            MEDIA_TYPE_CR_CATEGORY, f"{MEDIA_TYPE_CR_CATEGORY}:action"
        )
        assert cat_item_browse.media_content_type == MEDIA_TYPE_CR_CATEGORY

        # Test series browse
        series_browse = await player.async_browse_media(
            MEDIA_TYPE_CR_SERIES, f"{MEDIA_TYPE_CR_SERIES}:series-1"
        )
        assert series_browse.media_content_type == MediaType.TVSHOW

        # Test season browse
        season_browse = await player.async_browse_media(
            MEDIA_TYPE_CR_SEASON, f"{MEDIA_TYPE_CR_SEASON}:season-1"
        )
        assert season_browse.media_content_type == MediaType.SEASON

        # Test play_media service call
        await hass.services.async_call(
            "media_player",
            "play_media",
            {
                "entity_id": player_id,
                "media_content_type": MediaType.VIDEO,
                "media_content_id": "episode:ep-12345",
            },
            blocking=True,
        )
        await hass.async_block_till_done()

        updated_state = hass.states.get(player_id)
        assert updated_state is not None
        assert updated_state.state == MediaPlayerState.PLAYING
        assert (
            updated_state.attributes.get("media_content_id")
            == "https://www.crunchyroll.com/watch/ep-12345"
        )
