"""Tests for Crunchyroll select platform (profile switcher)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crunchyroll.api.models import CrunchyrollProfile
from custom_components.crunchyroll.const import CONF_EMAIL, CONF_PASSWORD, DOMAIN


@pytest.mark.asyncio
async def test_profile_select_entity(
    hass: HomeAssistant,
    mock_crunchyroll_client,
    mock_crunchyroll_data,
):
    """Test Crunchyroll select entity displays options and switches profile."""
    profile2 = CrunchyrollProfile(
        profile_id="pid-2",
        account_id="acc-12345",
        profile_name="Sub Profile",
        username="subuser",
    )
    mock_crunchyroll_data.profiles = [mock_crunchyroll_data.profile, profile2]
    mock_crunchyroll_client.get_profiles.return_value = mock_crunchyroll_data.profiles

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "secret_password",
        },
        entry_id="test_entry_id",
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.crunchyroll.CrunchyrollClient",
            return_value=mock_crunchyroll_client,
        ),
        patch(
            "custom_components.crunchyroll.coordinator.CrunchyrollClient",
            return_value=mock_crunchyroll_client,
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_id = "select.crunchyroll_animehero_profile"
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "AnimeHero"
    assert "Sub Profile" in state.attributes["options"]

    # Select sub profile
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id, "option": "Sub Profile"},
        blocking=True,
    )
    mock_crunchyroll_client.switch_profile.assert_called_with("pid-2")


@pytest.mark.asyncio
async def test_switch_profile_service(
    hass: HomeAssistant,
    mock_crunchyroll_client,
    mock_crunchyroll_data,
):
    """Test crunchyroll.switch_profile service."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: "test@example.com",
            CONF_PASSWORD: "secret_password",
        },
        entry_id="test_entry_id",
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.crunchyroll.CrunchyrollClient",
            return_value=mock_crunchyroll_client,
        ),
        patch(
            "custom_components.crunchyroll.coordinator.CrunchyrollClient",
            return_value=mock_crunchyroll_client,
        ),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.services.async_call(
        DOMAIN,
        "switch_profile",
        {"profile_id": "pid-99"},
        blocking=True,
        return_response=True,
    )
    mock_crunchyroll_client.switch_profile.assert_called_with("pid-99")
    assert result == {"success": True, "profile_id": "pid-99"}
