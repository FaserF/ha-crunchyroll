from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crunchyroll.api.exceptions import (
    AuthenticationError,
    ConnectionError,
)
from custom_components.crunchyroll.const import (
    CONF_AUDIO_LOCALE,
    CONF_EMAIL,
    CONF_LOCALE,
    CONF_PASSWORD,
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
                CONF_LOCALE: "de-DE",
                CONF_AUDIO_LOCALE: "ja-JP",
            },
        )
        assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result2["title"] == "Crunchyroll (AnimeHero)"
        assert result2["data"][CONF_EMAIL] == "test@example.com"


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
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL: 7200,
            CONF_LOCALE: "en-US",
            CONF_AUDIO_LOCALE: "ja-JP",
        },
    )
    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_SCAN_INTERVAL] == 7200
