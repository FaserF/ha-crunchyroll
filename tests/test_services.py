"""Tests for Crunchyroll custom list services."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.crunchyroll.const import DOMAIN


@pytest.mark.asyncio
async def test_create_custom_list_service(
    hass: HomeAssistant,
    mock_crunchyroll_client,
    mock_crunchyroll_data,
):
    """Service create_custom_list calls API and returns new list metadata."""
    entry = MockConfigEntry(domain=DOMAIN, data={"email": "a@b.com", "password": "pw"})
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
        "create_custom_list",
        {"title": "Test List"},
        blocking=True,
        return_response=True,
    )
    mock_crunchyroll_client.create_custom_list.assert_called_once_with(
        title="Test List"
    )
    assert result == {"list_id": "new-list-123", "title": "Test List"}


@pytest.mark.asyncio
async def test_add_to_custom_list_service(
    hass: HomeAssistant,
    mock_crunchyroll_client,
    mock_crunchyroll_data,
):
    """Service add_to_custom_list delegates to client and reports success."""
    entry = MockConfigEntry(domain=DOMAIN, data={"email": "a@b.com", "password": "pw"})
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
        "add_to_custom_list",
        {"list_id": "list-abc", "content_id": "GYZJ43JMR"},
        blocking=True,
        return_response=True,
    )
    mock_crunchyroll_client.add_to_custom_list.assert_called_once_with(
        list_id="list-abc", content_id="GYZJ43JMR"
    )
    assert result == {"success": True, "list_id": "list-abc", "content_id": "GYZJ43JMR"}


@pytest.mark.asyncio
async def test_remove_from_custom_list_service(
    hass: HomeAssistant,
    mock_crunchyroll_client,
    mock_crunchyroll_data,
):
    """Service remove_from_custom_list delegates to client and reports success."""
    entry = MockConfigEntry(domain=DOMAIN, data={"email": "a@b.com", "password": "pw"})
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
        "remove_from_custom_list",
        {"list_id": "list-abc", "content_id": "GYZJ43JMR"},
        blocking=True,
        return_response=True,
    )
    mock_crunchyroll_client.remove_from_custom_list.assert_called_once_with(
        list_id="list-abc", content_id="GYZJ43JMR"
    )
    assert result == {"success": True, "list_id": "list-abc", "content_id": "GYZJ43JMR"}
