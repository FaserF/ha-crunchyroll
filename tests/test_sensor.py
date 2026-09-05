from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crunchyroll.const import (
    ATTR_ACCOUNT_ID,
    ATTR_EMAIL,
    ATTR_EMAIL_VERIFIED,
    ATTR_HISTORY_COUNT,
    ATTR_IS_PREMIUM,
    ATTR_LAST_WATCHED,
    ATTR_PRODUCTS,
    ATTR_PROFILE_ID,
    ATTR_SUBSCRIPTION_TIER,
    ATTR_WATCHLIST_COUNT,
    CONF_EMAIL,
    CONF_PASSWORD,
    DOMAIN,
)


async def test_sensor_setup_and_state(
    hass: HomeAssistant, mock_crunchyroll_client
) -> None:
    """Test setting up Crunchyroll sensor and checking state & attributes."""
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

        state = hass.states.get("sensor.crunchyroll_animehero_account")
        if state is None:
            # Check any sensor in domain
            sensors = [
                s for s in hass.states.async_entity_ids("sensor") if "crunchyroll" in s
            ]
            assert len(sensors) > 0
            state = hass.states.get(sensors[0])

        assert state is not None
        assert state.state == "mega_fan"
        attrs = state.attributes
        assert attrs[ATTR_ACCOUNT_ID] == "acc-12345"
        assert attrs[ATTR_PROFILE_ID] == "acc-12345"
        assert attrs[ATTR_EMAIL] == "test@example.com"
        assert attrs[ATTR_EMAIL_VERIFIED] is True
        assert attrs[ATTR_IS_PREMIUM] is True
        assert attrs[ATTR_SUBSCRIPTION_TIER] == "mega_fan"
        assert "premium_tier_mega_fan" in attrs[ATTR_PRODUCTS]
        assert attrs[ATTR_WATCHLIST_COUNT] == 1
        assert attrs[ATTR_HISTORY_COUNT] == 1
        assert attrs[ATTR_LAST_WATCHED]["title"] == "Frieren: Beyond Journey's End"

        # Verify device registry configuration_url (Visit / Website button in HA UI)
        from homeassistant.helpers import device_registry as dr

        dev_reg = dr.async_get(hass)
        device = dev_reg.async_get_device_by_identifier(DOMAIN, "acc-12345")
        if device is None:
            device = dev_reg.async_get_device(identifiers={(DOMAIN, "acc-12345")})
        assert device is not None
        assert device.configuration_url == "https://www.crunchyroll.com"

        # Check dedicated sensors
        sensors = {
            s: hass.states.get(s) for s in hass.states.async_entity_ids("sensor")
        }
        wl_sensor = next(
            (v for k, v in sensors.items() if "watchlist" in k and v), None
        )
        assert wl_sensor is not None
        assert wl_sensor.state == "1"
        assert len(wl_sensor.attributes["items"]) == 1

        completed_sensor = next(
            (v for k, v in sensors.items() if "completed_animes" in k and v), None
        )
        assert completed_sensor is not None
        assert completed_sensor.state == "1"
        assert len(completed_sensor.attributes["completed_animes"]) == 1

        in_progress_sensor = next(
            (v for k, v in sensors.items() if "in_progress_animes" in k and v), None
        )
        assert in_progress_sensor is not None
        assert in_progress_sensor.state == "1"
        assert len(in_progress_sensor.attributes["in_progress_animes"]) == 1

        from homeassistant.helpers import entity_registry as er

        ent_reg = er.async_get(hass)

        # Enabled by default sensors
        simulcasts_sensor = next(
            (v for k, v in sensors.items() if "simulcasts" in k and v), None
        )
        assert simulcasts_sensor is not None
        assert simulcasts_sensor.state == "1"
        assert len(simulcasts_sensor.attributes["simulcasts"]) == 1

        new_ep_watched = next(
            (v for k, v in sensors.items() if "new_episodes_for_watched" in k and v),
            None,
        )
        assert new_ep_watched is not None
        assert new_ep_watched.state == "1"
        assert len(new_ep_watched.attributes["new_episodes_for_watched"]) == 1

        # Check sensors disabled by default in entity registry
        entry_new = ent_reg.async_get("sensor.crunchyroll_animehero_new_animes")
        assert entry_new is not None
        assert entry_new.disabled is True

        entry_pop = ent_reg.async_get("sensor.crunchyroll_animehero_popular_animes")
        assert entry_pop is not None
        assert entry_pop.disabled is True

        entry_mov = ent_reg.async_get("sensor.crunchyroll_animehero_movies")
        assert entry_mov is not None
        assert entry_mov.disabled is True

        entry_all_ep = ent_reg.async_get("sensor.crunchyroll_animehero_new_episodes")
        assert entry_all_ep is not None
        assert entry_all_ep.disabled is True

        entry_cl = ent_reg.async_get("sensor.crunchyroll_animehero_custom_lists")
        assert entry_cl is not None
        assert entry_cl.disabled is True
