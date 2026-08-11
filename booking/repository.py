"""Storage for bookings."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .models import Booking, BookingStatus


class BookingRepository(Protocol):
    """The seam between the booking rules and whatever stores them.

    A durable backend (SQL, etc.) satisfies this same interface, so the
    service never needs to know which one it is talking to.
    """

    def add(self, booking: Booking) -> None:
        """Store a new booking."""

    def get(self, booking_id: str) -> Booking | None:
        """Return the booking with this id, or ``None`` if there is none."""

    def update(self, booking: Booking) -> None:
        """Replace the stored booking that shares this booking's id."""

    def list_for_resource(
        self, resource_id: str, window_start: datetime, window_end: datetime
    ) -> list[Booking]:
        """Return active bookings for the resource intersecting the window."""

    def list_for_user(self, user_id: str) -> list[Booking]:
        """Return every booking belonging to the user, active or cancelled."""


class InMemoryBookingRepository:
    """Dict-backed :class:`BookingRepository`, suitable for tests and demos.

    ``list_for_resource`` scans every stored booking. That is correct but
    linear; a real backend would push the same filter into an indexed query
    on ``(resource_id, start_time)``.
    """

    def __init__(self) -> None:
        self._bookings: dict[str, Booking] = {}

    def add(self, booking: Booking) -> None:
        self._bookings[booking.id] = booking

    def get(self, booking_id: str) -> Booking | None:
        return self._bookings.get(booking_id)

    def update(self, booking: Booking) -> None:
        self._bookings[booking.id] = booking

    def list_for_resource(
        self, resource_id: str, window_start: datetime, window_end: datetime
    ) -> list[Booking]:
        # Half-open intervals: a booking ending exactly at window_start, or
        # starting exactly at window_end, does not intersect the window.
        return sorted(
            (
                booking
                for booking in self._bookings.values()
                if booking.resource_id == resource_id
                and booking.status is BookingStatus.CONFIRMED
                and booking.start_time < window_end
                and booking.end_time > window_start
            ),
            key=lambda booking: booking.start_time,
        )

    def list_for_user(self, user_id: str) -> list[Booking]:
        return sorted(
            (b for b in self._bookings.values() if b.user_id == user_id),
            key=lambda booking: booking.start_time,
        )
