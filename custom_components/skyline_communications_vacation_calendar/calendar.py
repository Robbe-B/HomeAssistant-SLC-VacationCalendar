"""Skyline Communications Vacation Calendar."""

from datetime import datetime, date, time, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    DOMAIN_METRICS_URL,
    MANUFACTURER_NAME,
    MODEL_NAME,
    SERVICE_NAME,
)
from .coordinator import CalendarCoordinator
from .skyline.calendar_api import CalendarEntry, CalendarEntryType


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Skyline Communications Vacation Calendar entry."""
    coordinator: CalendarCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities(
        [
            SLCVacationCalendarEntity(
                config_entry.title, config_entry.entry_id, coordinator
            )
        ]
    )


class SLCVacationCalendarEntity(CoordinatorEntity, CalendarEntity):
    """Representation of a Skyline Communications Calendar element."""

    _attr_has_entity_name = True
    _entries: list[CalendarEntry] | None = None
    coordinator: CalendarCoordinator

    def __init__(
        self, name: str, unique_id: str, coordinator: CalendarCoordinator
    ) -> None:
        """Initialize SLCVacationCalendarEntity."""
        super().__init__(coordinator)
        self._attr_unique_id = unique_id
        self._entries = self.coordinator.entries
        self._event = self.get_current_or_upcoming_event(self._entries)

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        return self._event

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        self._entries = self.coordinator.entries
        self._event = self.get_current_or_upcoming_event(self._entries)
        self.async_write_ha_state()

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""

        event_list: list[CalendarEvent] = []

        if self._entries is not None:
            for event in self._entries:
                if start_date <= event.event_date <= end_date:
                    event = self.get_calendar_event_from_calender_entry(event)
                    event_list.append(event)

        return event_list

    def get_current_or_upcoming_event(
        self, events: list[CalendarEntry]
    ) -> CalendarEvent | None:
        """Return the current ongoing event if it exists, otherwise the next upcoming event. Return None if no relevant events exist."""

        # Current time with system timezone
        now = datetime.now().astimezone()

        current_event = None
        future_events = []

        for e in events:
            if e.event_date <= now < e.end_date:
                # Currently ongoing
                current_event = e
                break  # stop at first ongoing event
            elif e.event_date > now:
                # Future events
                future_events.append(e)

        if current_event:
            return self.get_calendar_event_from_calender_entry(current_event)

        if future_events:
            # Next upcoming event
            next_event = min(future_events, key=lambda e: e.event_date)
            return self.get_calendar_event_from_calender_entry(next_event)

        return None

    def get_calendar_event_from_calender_entry(
        self, calendarEntry: CalendarEntry
    ) -> CalendarEvent:
        """Converts a CalendarEntry to a CalendarEvent."""
        return self.normalize_calendar_event(
            CalendarEvent(
                uid=calendarEntry.id,
                summary=calendarEntry.category.name,
                start=calendarEntry.event_date,
                end=calendarEntry.end_date,
                description=calendarEntry.description,
            )
        )

    def is_all_day_or_multi_day_calendar_event(self, event: CalendarEvent) -> bool:
        """Detects single or multi day events that are 'all day long'."""
        start = event.start
        end = event.end

        # ----- CASE 1: Native HA all-day event (uses date objects) -----
        if (
            isinstance(start, date)
            and not isinstance(start, datetime)
            and isinstance(end, date)
            and not isinstance(end, datetime)
        ):
            return True

        # ----- CASE 2: datetime base => 00:00 → 23:59 or 00:00 → 00:00  -----
        if isinstance(start, datetime) and isinstance(end, datetime):
            # Normalize seconds
            start = start.replace(second=0)
            end = end.replace(second=0)

            midnight = time(0, 0, 0)
            almost_midnight = time(23, 59, 0)

            if (start.time() == midnight and end.time() == almost_midnight) or (
                start.time() == midnight
                and end.time() == midnight
                and start.date() != end.date()
            ):
                return True

        return False

    def normalize_calendar_event(self, event: CalendarEvent) -> CalendarEvent:
        """Return a new Home Assistant–normalized CalendarEvent."""
        if self.is_all_day_or_multi_day_calendar_event(event):
            # Convert start to date if datetime
            if isinstance(event.start, datetime):
                event.start = event.start.date()
            # Convert end to date if datetime
            if isinstance(event.end, datetime):
                event.end = event.end.date()

            # HA: end is *exclusive*, so always +1 day
            event.end = event.end + timedelta(days=1)
        return event

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            name=SERVICE_NAME,
            manufacturer=MANUFACTURER_NAME,
            model=MODEL_NAME,
            identifiers={
                (
                    DOMAIN,
                    f"slc-vaction-calendar-{self.coordinator.fullname}",
                )
            },
            configuration_url=DOMAIN_METRICS_URL,
        )
