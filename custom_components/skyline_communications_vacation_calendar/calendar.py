"""Skyline Communications Vacation Calendar."""

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .CalendarApi import CalendarEntry, CalendarEntryType
from .const import (
    DOMAIN,
    DOMAIN_METRICS_URL,
    MANUFACTURER_NAME,
    MODEL_NAME,
    SERVICE_NAME,
)
from .coordinator import CalendarCoordinator


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
        self._event = self.get_next_upcoming_event(self._entries)

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        return self._event

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        self._entries = self.coordinator.entries
        self._event = self.get_next_upcoming_event(self._entries)
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

    def get_next_upcoming_event(
        self, events: list[CalendarEntry]
    ) -> CalendarEvent | None:
        """Return the calender entry with the closest future event_date, or None if none exist."""

        # Get current time with system timezone
        now = datetime.now().astimezone()

        # Filter to events strictly in the future
        future_events = [e for e in events if e.event_date > now]

        if not future_events:
            return None

        # get the event with the smallest (earliest) event_date
        return self.get_calendar_event_from_calender_entry(
            min(future_events, key=lambda e: e.event_date)
        )

    def get_calendar_event_from_calender_entry(
        self, calendarEntry: CalendarEntry
    ) -> CalendarEvent:
        """Converts a CalendarEntry to a CalendarEvent."""
        return CalendarEvent(
            uid=calendarEntry.id,
            summary=calendarEntry.category.name,
            start=calendarEntry.event_date,
            end=calendarEntry.end_date,
            description=calendarEntry.description,
        )

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
