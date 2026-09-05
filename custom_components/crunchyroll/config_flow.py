from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

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
    CONF_AUTO_REMOVE_WATCHED_FROM_WATCHLIST,
    CONF_DEVICE_ID,
    CONF_EMAIL,
    CONF_LOCALE,
    CONF_PASSWORD,
    CONF_PROFILE_ID,
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
    }
)


class CrunchyrollConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Crunchyroll."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._user_input: dict[str, Any] = {}
        self._profiles: list[Any] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            device_id = self._user_input.get(CONF_DEVICE_ID) or str(uuid4())
            client = CrunchyrollClient(
                email=email,
                password=user_input[CONF_PASSWORD],
                device_id=device_id,
            )
            try:
                await client.login()
                profiles = await client.get_profiles()
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
                self._user_input = {**user_input, CONF_DEVICE_ID: device_id}
                self._profiles = profiles

                primary_account_id = (
                    profiles[0].account_id or profiles[0].profile_id or email
                )
                await self.async_set_unique_id(primary_account_id)
                self._abort_if_unique_id_configured()

                if len(profiles) > 1:
                    return await self.async_step_profile()

                selected = profiles[0]
                return self._create_entry_from_profile(selected)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle profile selection step if multiple profiles exist."""
        if user_input is not None:
            chosen_id = user_input[CONF_PROFILE_ID]
            selected_profile = next(
                (
                    p
                    for p in self._profiles
                    if (p.profile_id or p.account_id) == chosen_id
                ),
                self._profiles[0],
            )
            return self._create_entry_from_profile(selected_profile)

        profile_options = {
            (p.profile_id or p.account_id): p.profile_name or p.username or p.profile_id
            for p in self._profiles
        }
        first_id = self._profiles[0].profile_id or self._profiles[0].account_id

        schema = vol.Schema(
            {
                vol.Required(CONF_PROFILE_ID, default=first_id): vol.In(
                    profile_options
                ),
            }
        )

        return self.async_show_form(
            step_id="profile",
            data_schema=schema,
        )

    def _create_entry_from_profile(self, profile: Any) -> ConfigFlowResult:
        """Create entry from chosen profile."""
        detected_locale = profile.preferred_communication_language or DEFAULT_LOCALE
        detected_audio = (
            profile.preferred_content_audio_language or DEFAULT_AUDIO_LOCALE
        )

        entry_data = {
            CONF_EMAIL: self._user_input[CONF_EMAIL],
            CONF_PASSWORD: self._user_input[CONF_PASSWORD],
            CONF_DEVICE_ID: self._user_input.get(CONF_DEVICE_ID) or str(uuid4()),
            CONF_PROFILE_ID: profile.profile_id or profile.account_id,
            CONF_LOCALE: detected_locale,
            CONF_AUDIO_LOCALE: detected_audio,
        }

        title = profile.profile_name or profile.username or self._user_input[CONF_EMAIL]
        return self.async_create_entry(
            title=f"Crunchyroll ({title})",
            data=entry_data,
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

    def __init__(self) -> None:
        """Initialize options flow handler."""
        self._profiles: list[Any] = []

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

        # Retrieve available profiles via coordinator or direct client
        if not self._profiles:
            coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
            if coordinator and coordinator.client:
                try:
                    self._profiles = await coordinator.client.get_profiles()
                except Exception:  # noqa: BLE001
                    self._profiles = []
            if not self._profiles:
                device_id = self.config_entry.data.get(
                    CONF_DEVICE_ID, self.config_entry.entry_id
                )
                client = CrunchyrollClient(
                    email=self.config_entry.data[CONF_EMAIL],
                    password=self.config_entry.data[CONF_PASSWORD],
                    device_id=device_id,
                )
                try:
                    await client.login()
                    self._profiles = await client.get_profiles()
                    await client.close()
                except Exception:  # noqa: BLE001
                    self._profiles = []

        options = self.config_entry.options
        current_interval = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        if current_interval < MIN_SCAN_INTERVAL:
            current_interval = DEFAULT_SCAN_INTERVAL

        current_profile_id = options.get(
            CONF_PROFILE_ID,
            self.config_entry.data.get(CONF_PROFILE_ID),
        )

        schema_fields: dict[Any, Any] = {}

        if len(self._profiles) > 1:
            profile_options = {
                (p.profile_id or p.account_id): p.profile_name
                or p.username
                or p.profile_id
                for p in self._profiles
            }
            default_pid = (
                current_profile_id
                if current_profile_id in profile_options
                else (self._profiles[0].profile_id or self._profiles[0].account_id)
            )
            schema_fields[vol.Optional(CONF_PROFILE_ID, default=default_pid)] = vol.In(
                profile_options
            )

        schema_fields[
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=current_interval,
            )
        ] = cv.positive_int
        schema_fields[
            vol.Optional(
                CONF_LOCALE,
                default=options.get(CONF_LOCALE, DEFAULT_LOCALE),
            )
        ] = str
        schema_fields[
            vol.Optional(
                CONF_AUDIO_LOCALE,
                default=options.get(CONF_AUDIO_LOCALE, DEFAULT_AUDIO_LOCALE),
            )
        ] = str
        schema_fields[
            vol.Optional(
                CONF_AUTO_REMOVE_WATCHED_FROM_WATCHLIST,
                default=options.get(CONF_AUTO_REMOVE_WATCHED_FROM_WATCHLIST, False),
            )
        ] = bool

        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(schema_fields), errors=errors
        )
