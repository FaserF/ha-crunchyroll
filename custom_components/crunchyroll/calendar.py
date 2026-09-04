from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api.models import CrunchyrollItem
from .const import DOMAIN
from .coordinator import CrunchyrollDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Crunchyroll calendar entity based on a config entry."""
    coordinator: CrunchyrollDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([CrunchyrollReleasesCalendarEntity(coordinator, entry)])


def _parse_iso_datetime(date_str: str | None) -> datetime | None:
    """Parse ISO 8601 string to aware datetime."""
    if not date_str:
        return None
    try:
        cleaned = date_str.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None


class CrunchyrollReleasesCalendarEntity(
    CoordinatorEntity[CrunchyrollDataUpdateCoordinator], CalendarEntity
):
    """Calendar entity displaying Crunchyroll anime episode releases."""

    _attr_has_entity_name = True
    _attr_translation_key = "releases"
    _attr_icon = "mdi:calendar-clock"

    def __init__(
        self,
        coordinator: CrunchyrollDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        account_id = (
            coordinator.data.profile.account_id
            if coordinator.data and coordinator.data.profile
            else entry.entry_id
        ) or entry.entry_id
        self._attr_unique_id = f"{account_id}_releases"

        profile_name = "Account"
        if coordinator.data and coordinator.data.profile:
            profile_name = (
                coordinator.data.profile.profile_name
                or coordinator.data.profile.username
                or "Account"
            )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, account_id)},
            name=f"Crunchyroll ({profile_name})",
            manufacturer="Crunchyroll",
            model="Streaming Account",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.crunchyroll.com",
        )

    def _item_to_calendar_event(self, item: CrunchyrollItem) -> CalendarEvent | None:
        """Convert a CrunchyrollItem (episode) to a CalendarEvent."""
        start_dt = _parse_iso_datetime(item.release_date or item.date_played)
        if not start_dt:
            return None

        dur_seconds = (
            int(item.duration_ms / 1000)
            if item.duration_ms and item.duration_ms > 0
            else 1440
        )
        end_dt = start_dt + timedelta(seconds=dur_seconds)

        summary = item.display_title
        desc = (
            f"Series: {item.series_title or 'Unknown'}\n"
            f"Episode: {item.episode_number or 'N/A'}\n\n"
            f"{item.description or ''}"
        ).strip()

        return CalendarEvent(
            start=start_dt,
            end=end_dt,
            summary=summary,
            description=desc,
            location=item.crunchyroll_url,
            uid=item.id,
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming or current event."""
        if not self.coordinator.data or not self.coordinator.data.new_episodes:
            return None

        now = datetime.now(ZoneInfo("UTC"))
        upcoming_events: list[CalendarEvent] = []

        for item in self.coordinator.data.new_episodes:
            event = self._item_to_calendar_event(item)
            if event and event.end >= now:
                upcoming_events.append(event)

        if not upcoming_events:
            all_events = [
                ev
                for item in self.coordinator.data.new_episodes
                if (ev := self._item_to_calendar_event(item)) is not None
            ]
            if all_events:
                all_events.sort(key=lambda ev: ev.start, reverse=True)
                return all_events[0]
            return None

        upcoming_events.sort(key=lambda ev: ev.start)
        return upcoming_events[0]

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        if not self.coordinator.data:
            return []

        tz = ZoneInfo("UTC")
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=tz)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=tz)

        events: list[CalendarEvent] = []
        for item in self.coordinator.data.new_episodes:
            ev = self._item_to_calendar_event(item)
            if not ev:
                continue
            ev_start = (
                ev.start
                if isinstance(ev.start, datetime)
                else datetime.combine(ev.start, datetime.min.time(), tzinfo=tz)
            )
            ev_end = (
                ev.end
                if isinstance(ev.end, datetime)
                else datetime.combine(ev.end, datetime.min.time(), tzinfo=tz)
            )

            if ev_start.tzinfo is None:
                ev_start = ev_start.replace(tzinfo=tz)
            if ev_end.tzinfo is None:
                ev_end = ev_end.replace(tzinfo=tz)

            if ev_start < end_date and ev_end > start_date:
                events.append(ev)

        events.sort(key=lambda x: x.start)
        return events
