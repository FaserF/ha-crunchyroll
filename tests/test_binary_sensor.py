from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crunchyroll.const import CONF_EMAIL, CONF_PASSWORD, DOMAIN


async def test_binary_sensor_premium(
    hass: HomeAssistant, mock_crunchyroll_client
) -> None:
    """Test binary sensor reflecting premium status."""
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

        binary_sensors = [
            s
            for s in hass.states.async_entity_ids("binary_sensor")
            if "crunchyroll" in s
        ]
        assert len(binary_sensors) > 0
        state = hass.states.get(binary_sensors[0])
        assert state is not None
        assert state.state == "on"
        assert state.attributes["tier"] == "mega_fan"
