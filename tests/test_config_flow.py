from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crunchyroll.api.exceptions import (
    AuthenticationError,
    ConnectionError,
)
from custom_components.crunchyroll.api.models import CrunchyrollProfile
from custom_components.crunchyroll.const import (
    CONF_AUDIO_LOCALE,
    CONF_EMAIL,
    CONF_LOCALE,
    CONF_PASSWORD,
    CONF_PROFILE_ID,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)


async def test_flow_user_success(hass: HomeAssistant, mock_crunchyroll_client) -> None:
    """Test standard successful config flow."""
    with patch(
        "custom_components.crunchyroll.config_flow.CrunchyrollClient",
        return_value=mock_crunchyroll_client,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "user"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "test@example.com",
                CONF_PASSWORD: "secret_password",
            },
        )
        assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result2["title"] == "Crunchyroll (AnimeHero)"
        assert result2["data"][CONF_EMAIL] == "test@example.com"
        assert result2["data"][CONF_LOCALE] == "de-DE"
        assert result2["data"][CONF_AUDIO_LOCALE] == "ja-JP"
        assert len(result2["data"]["device_id"]) > 0


async def test_flow_user_invalid_auth(
    hass: HomeAssistant, mock_crunchyroll_client
) -> None:
    """Test auth failure handling."""
    mock_crunchyroll_client.login.side_effect = AuthenticationError("Auth failed")
    with patch(
        "custom_components.crunchyroll.config_flow.CrunchyrollClient",
        return_value=mock_crunchyroll_client,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "bad@example.com",
                CONF_PASSWORD: "wrong",
            },
        )
        assert result2["type"] == data_entry_flow.FlowResultType.FORM
        assert result2["errors"] == {"base": "invalid_auth"}


async def test_flow_user_cannot_connect(
    hass: HomeAssistant, mock_crunchyroll_client
) -> None:
    """Test connection error handling."""
    mock_crunchyroll_client.login.side_effect = ConnectionError("Network down")
    with patch(
        "custom_components.crunchyroll.config_flow.CrunchyrollClient",
        return_value=mock_crunchyroll_client,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "bad@example.com",
                CONF_PASSWORD: "wrong",
            },
        )
        assert result2["type"] == data_entry_flow.FlowResultType.FORM
        assert result2["errors"] == {"base": "cannot_connect"}


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_EMAIL: "user@example.com", CONF_PASSWORD: "pw"},
        options={CONF_SCAN_INTERVAL: 86400},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    # Test error when scan_interval < 3600
    invalid_result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL: 1800,
            CONF_LOCALE: "en-US",
            CONF_AUDIO_LOCALE: "ja-JP",
        },
    )
    assert invalid_result["type"] == data_entry_flow.FlowResultType.FORM
    assert invalid_result["errors"] == {CONF_SCAN_INTERVAL: "min_scan_interval"}

    # Test successful configuration with valid interval >= 3600
    from custom_components.crunchyroll.const import (
        CONF_AUTO_REMOVE_WATCHED_FROM_WATCHLIST,
    )

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL: 7200,
            CONF_LOCALE: "en-US",
            CONF_AUDIO_LOCALE: "ja-JP",
            CONF_AUTO_REMOVE_WATCHED_FROM_WATCHLIST: True,
        },
    )
    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_SCAN_INTERVAL] == 7200
    assert result2["data"][CONF_AUTO_REMOVE_WATCHED_FROM_WATCHLIST] is True


async def test_flow_user_multiple_profiles(
    hass: HomeAssistant, mock_crunchyroll_client
) -> None:
    """Test config flow with multiple profiles selecting second profile."""
    prof1 = CrunchyrollProfile(
        account_id="acc-123",
        profile_id="prof-1",
        profile_name="Profile One",
        preferred_communication_language="en-US",
        preferred_content_audio_language="ja-JP",
    )
    prof2 = CrunchyrollProfile(
        account_id="acc-123",
        profile_id="prof-2",
        profile_name="Profile Two",
        preferred_communication_language="de-DE",
        preferred_content_audio_language="de-DE",
    )
    mock_crunchyroll_client.get_profiles.return_value = [prof1, prof2]

    with patch(
        "custom_components.crunchyroll.config_flow.CrunchyrollClient",
        return_value=mock_crunchyroll_client,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "user"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "multi@example.com",
                CONF_PASSWORD: "secret_password",
            },
        )
        assert result2["type"] == data_entry_flow.FlowResultType.FORM
        assert result2["step_id"] == "profile"

        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_PROFILE_ID: "prof-2",
            },
        )
        assert result3["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result3["title"] == "Crunchyroll (Profile Two)"
        assert result3["data"][CONF_PROFILE_ID] == "prof-2"
        assert result3["data"][CONF_LOCALE] == "de-DE"
        assert result3["data"][CONF_AUDIO_LOCALE] == "de-DE"


async def test_options_flow_multiple_profiles(
    hass: HomeAssistant, mock_crunchyroll_client
) -> None:
    """Test options flow allows selecting profile when multiple exist."""
    prof1 = CrunchyrollProfile(
        account_id="acc-123",
        profile_id="prof-1",
        profile_name="Profile One",
    )
    prof2 = CrunchyrollProfile(
        account_id="acc-123",
        profile_id="prof-2",
        profile_name="Profile Two",
    )
    mock_crunchyroll_client.get_profiles.return_value = [prof1, prof2]

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: "user@example.com",
            CONF_PASSWORD: "pw",
            CONF_PROFILE_ID: "prof-1",
        },
        options={CONF_SCAN_INTERVAL: 86400},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.crunchyroll.config_flow.CrunchyrollClient",
        return_value=mock_crunchyroll_client,
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "init"
        assert CONF_PROFILE_ID in result["data_schema"].schema

        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_PROFILE_ID: "prof-2",
                CONF_SCAN_INTERVAL: 3600,
                CONF_LOCALE: "de-DE",
                CONF_AUDIO_LOCALE: "de-DE",
            },
        )
        assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result2["data"][CONF_PROFILE_ID] == "prof-2"


async def test_reauth_flow_success(
    hass: HomeAssistant, mock_crunchyroll_client
) -> None:
    """Test reauth flow successfully updates config entry credentials."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="acc-123",
        data={
            CONF_EMAIL: "old@example.com",
            CONF_PASSWORD: "old_password",
            "device_id": "test-device-id",
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.crunchyroll.config_flow.CrunchyrollClient",
        return_value=mock_crunchyroll_client,
    ):
        result = await entry.start_reauth_flow(hass)
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "new@example.com",
                CONF_PASSWORD: "new_password",
            },
        )
        assert result2["type"] == data_entry_flow.FlowResultType.ABORT
        assert result2["reason"] == "reauth_successful"
        assert entry.data[CONF_EMAIL] == "new@example.com"
        assert entry.data[CONF_PASSWORD] == "new_password"


async def test_reauth_flow_invalid_auth(
    hass: HomeAssistant, mock_crunchyroll_client
) -> None:
    """Test reauth flow handles invalid credentials."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="acc-123",
        data={
            CONF_EMAIL: "old@example.com",
            CONF_PASSWORD: "old_password",
        },
    )
    entry.add_to_hass(hass)

    mock_crunchyroll_client.login.side_effect = AuthenticationError(
        "Invalid credentials"
    )

    with patch(
        "custom_components.crunchyroll.config_flow.CrunchyrollClient",
        return_value=mock_crunchyroll_client,
    ):
        result = await entry.start_reauth_flow(hass)
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "old@example.com",
                CONF_PASSWORD: "wrong_password",
            },
        )
        assert result2["type"] == data_entry_flow.FlowResultType.FORM
        assert result2["errors"] == {"base": "invalid_auth"}


async def test_options_flow_update_credentials(
    hass: HomeAssistant, mock_crunchyroll_client
) -> None:
    """Test updating credentials directly via options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: "old@example.com",
            CONF_PASSWORD: "old_password",
            "device_id": "test-device-id",
        },
        options={CONF_SCAN_INTERVAL: 3600},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.crunchyroll.config_flow.CrunchyrollClient",
        return_value=mock_crunchyroll_client,
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] == data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "init"

        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_EMAIL: "updated@example.com",
                CONF_PASSWORD: "updated_password",
                CONF_SCAN_INTERVAL: 7200,
                CONF_LOCALE: "de-DE",
                CONF_AUDIO_LOCALE: "ja-JP",
            },
        )
        assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert entry.data[CONF_EMAIL] == "updated@example.com"
        assert entry.data[CONF_PASSWORD] == "updated_password"
        assert entry.options[CONF_SCAN_INTERVAL] == 7200
