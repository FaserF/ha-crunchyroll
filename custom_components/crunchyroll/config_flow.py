from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .api.client import CrunchyrollClient
from .api.exceptions import AuthenticationError, ConnectionError, CrunchyrollError
from .const import (
    CONF_AUDIO_LOCALE,
    CONF_EMAIL,
    CONF_LOCALE,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    DEFAULT_AUDIO_LOCALE,
    DEFAULT_LOCALE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_LOCALE, default=DEFAULT_LOCALE): str,
        vol.Optional(CONF_AUDIO_LOCALE, default=DEFAULT_AUDIO_LOCALE): str,
    }
)


class CrunchyrollConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Crunchyroll."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            client = CrunchyrollClient(
                email=email,
                password=user_input[CONF_PASSWORD],
                locale=user_input.get(CONF_LOCALE, DEFAULT_LOCALE),
                preferred_audio_language=user_input.get(
                    CONF_AUDIO_LOCALE, DEFAULT_AUDIO_LOCALE
                ),
            )
            try:
                await client.login()
                profile = await client.get_profile()
                await client.close()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except CrunchyrollError:
                errors["base"] = "unknown"
            except Exception as exc:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during Crunchyroll login: %s", exc)
                errors["base"] = "unknown"
            else:
                account_id = profile.account_id or email
                await self.async_set_unique_id(account_id)
                self._abort_if_unique_id_configured()

                title = profile.profile_name or profile.username or email
                return self.async_create_entry(
                    title=f"Crunchyroll ({title})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> CrunchyrollOptionsFlowHandler:
        """Get the options flow for this handler."""
        return CrunchyrollOptionsFlowHandler()


class CrunchyrollOptionsFlowHandler(OptionsFlow):
    """Handle Crunchyroll options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if (
                user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                < MIN_SCAN_INTERVAL
            ):
                errors[CONF_SCAN_INTERVAL] = "min_scan_interval"
            else:
                return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        current_interval = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        if current_interval < MIN_SCAN_INTERVAL:
            current_interval = DEFAULT_SCAN_INTERVAL

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=current_interval,
                ): cv.positive_int,
                vol.Optional(
                    CONF_LOCALE,
                    default=options.get(CONF_LOCALE, DEFAULT_LOCALE),
                ): str,
                vol.Optional(
                    CONF_AUDIO_LOCALE,
                    default=options.get(CONF_AUDIO_LOCALE, DEFAULT_AUDIO_LOCALE),
                ): str,
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=data_schema, errors=errors
        )
