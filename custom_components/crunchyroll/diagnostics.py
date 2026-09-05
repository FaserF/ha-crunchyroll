"""Diagnostics support for Crunchyroll integration."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_EMAIL, DOMAIN
from .coordinator import CrunchyrollDataUpdateCoordinator

REDACT_KEYS = {
    CONF_PASSWORD,
    CONF_EMAIL,
    "password",
    "email",
    "access_token",
    "refresh_token",
    "account_id",
}


def _to_json_safe(obj: Any) -> Any:
    """Convert to JSON safe."""
    if isinstance(obj, bool) or obj is None:
        return obj
    if isinstance(obj, (int, str)):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return str(obj)
        return obj
    if isinstance(obj, (list, tuple, set)):
        return [_to_json_safe(i) for i in obj]
    if isinstance(obj, dict):
        return {str(k): _to_json_safe(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        return _to_json_safe(obj.__dict__)
    return str(obj)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for Crunchyroll config entry."""
    coordinator: CrunchyrollDataUpdateCoordinator = hass.data.get(DOMAIN, {}).get(
        entry.entry_id
    )
    if not coordinator:
        return {"error": "Coordinator not found"}

    diag: dict[str, Any] = {
        "config_entry": async_redact_data(dict(entry.data), REDACT_KEYS),
        "options": async_redact_data(dict(entry.options), REDACT_KEYS),
        "coordinator_last_update_success": coordinator.last_update_success,
    }

    if coordinator.data:
        data = coordinator.data
        diag["profile"] = {
            "account_id": "[REDACTED]",
            "email_verified": data.profile.email_verified,
            "maturity_rating": data.profile.maturity_rating,
            "preferred_communication_language": data.profile.preferred_communication_language,
        }
        diag["subscription"] = {
            "is_premium": data.subscription.is_premium,
            "tier": data.subscription.tier,
            "products_count": len(data.subscription.products),
        }
        diag["stats"] = {
            "watchlist_count": len(data.watchlist),
            "history_count": len(data.history),
            "recommendations_count": len(data.recommendations),
        }

    reg_devices = []
    reg_entities = []

    try:
        dev_reg = dr.async_get(hass)
        ent_reg = er.async_get(hass)

        for dev in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
            reg_devices.append(
                {
                    "id": str(dev.id),
                    "name": str(dev.name or ""),
                    "model": str(dev.model or ""),
                    "manufacturer": str(dev.manufacturer or ""),
                }
            )

        for ent in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
            reg_entities.append(
                {
                    "entity_id": str(ent.entity_id),
                    "unique_id": str(ent.unique_id),
                    "domain": str(ent.domain),
                    "disabled": ent.disabled_by is not None,
                }
            )
    except Exception as err:
        diag["registry_debug_error"] = str(err)

    diag["registry_debug"] = {
        "devices": reg_devices,
        "entities": reg_entities,
    }

    return _to_json_safe(diag)
