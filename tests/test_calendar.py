from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crunchyroll.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    DOMAIN,
)


async def test_calendar_setup_and_events(
    hass: HomeAssistant, mock_crunchyroll_client
) -> None:
    """Test Crunchyroll calendar entity setup and fetching events."""
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

        calendar_entities = hass.states.async_entity_ids("calendar")
        assert len(calendar_entities) >= 1
        cal_id = next(
            (c for c in calendar_entities if "releases" in c or "crunchyroll" in c),
            calendar_entities[0],
        )

        state = hass.states.get(cal_id)
        assert state is not None

        # Verify calendar entity via component
        from custom_components.crunchyroll.calendar import (
            CrunchyrollReleasesCalendarEntity,
        )

        coord = hass.data[DOMAIN][entry.entry_id]
        cal_entity = CrunchyrollReleasesCalendarEntity(coord, entry)

        start = datetime(2026, 9, 1, tzinfo=ZoneInfo("UTC"))
        end = datetime(2026, 9, 10, tzinfo=ZoneInfo("UTC"))
        events = await cal_entity.async_get_events(hass, start, end)

        assert len(events) >= 1
        assert "Frieren" in events[0].summary
        assert events[0].uid == "item-001"
