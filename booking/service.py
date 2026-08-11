"""Booking operations that need to consider other bookings."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from .errors import (
    BookingConflictError,
    BookingNotFoundError,
    BookingStateError,
)
from .models import Booking, BookingStatus, as_utc
from .policy import BookingPolicy, check_all
from .repository import BookingRepository


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BookingService:
    """Creates and transitions bookings, enforcing the scheduling rules.

    The clock and id factory are injected so that every rule involving "now"
    or an identifier can be pinned exactly in tests.
    """

    def __init__(
        self,
        repository: BookingRepository,
        *,
        policy: BookingPolicy | None = None,
        clock: Callable[[], datetime] = _utc_now,
        id_factory: Callable[[], str] = lambda: str(uuid4()),
    ) -> None:
        self._repository = repository
        self._policy = policy or BookingPolicy()
        self._clock = clock
        self._id_factory = id_factory

    # -- queries ------------------------------------------------------------

    def get_booking(self, booking_id: str) -> Booking:
        """Return a booking, raising if it does not exist."""
        booking = self._repository.get(booking_id)
        if booking is None:
            raise BookingNotFoundError(f"No booking with id {booking_id!r}.")
        return booking

    def list_bookings_for_user(self, user_id: str) -> list[Booking]:
        """Return the user's bookings, earliest first, including cancelled ones."""
        return self._repository.list_for_user(user_id)

    # -- commands -----------------------------------------------------------

    def create_booking(
        self,
        user_id: str,
        resource_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Booking:
        """Create a booking after checking it against every scheduling rule.

        Raises:
            BookingValidationError: The window breaks a time-only rule (lead
                time, duration, business hours).
            BookingConflictError: The window overlaps an existing booking for
                the same resource.
        """
        start = as_utc(start_time, "start_time")
        end = as_utc(end_time, "end_time")

        check_all(start, end, self._now(), self._policy)
        self._assert_no_overlap(resource_id, start, end)

        booking = Booking(
            id=self._id_factory(),
            user_id=user_id,
            resource_id=resource_id,
            start_time=start,
            end_time=end,
        )
        self._repository.add(booking)
        return booking

    def cancel_booking(self, booking_id: str) -> Booking:
        """Cancel a booking, freeing its slot for other bookings.

        Raises:
            BookingNotFoundError: No such booking.
            BookingStateError: Already cancelled, or already under way.
        """
        booking = self.get_booking(booking_id)

        if booking.status is BookingStatus.CANCELLED:
            raise BookingStateError(f"Booking {booking_id!r} is already cancelled.")
        if booking.start_time <= self._now():
            raise BookingStateError(
                f"Booking {booking_id!r} started at {booking.start_time.isoformat()} "
                "and can no longer be cancelled."
            )

        cancelled = dataclasses.replace(booking, status=BookingStatus.CANCELLED)
        self._repository.update(cancelled)
        return cancelled

    def reschedule_booking(
        self, booking_id: str, start_time: datetime, end_time: datetime
    ) -> Booking:
        """Move a booking to a new window, re-checking every creation rule.

        The lead time is measured from *now*, not from the original booking, so
        a booking cannot be dragged into the next 24 hours.

        Raises:
            BookingNotFoundError: No such booking.
            BookingStateError: The booking is cancelled.
            BookingValidationError: The new window breaks a time-only rule.
            BookingConflictError: The new window overlaps a *different* booking.
        """
        booking = self.get_booking(booking_id)
        if booking.status is BookingStatus.CANCELLED:
            raise BookingStateError(f"Booking {booking_id!r} is cancelled and cannot be moved.")

        start = as_utc(start_time, "start_time")
        end = as_utc(end_time, "end_time")

        check_all(start, end, self._now(), self._policy)
        # Exclude the booking being moved: otherwise its own unchanged record
        # counts as a conflict and no reschedule could ever succeed.
        self._assert_no_overlap(booking.resource_id, start, end, exclude_id=booking.id)

        moved = dataclasses.replace(booking, start_time=start, end_time=end)
        self._repository.update(moved)
        return moved

    # -- internals ----------------------------------------------------------

    def _now(self) -> datetime:
        return as_utc(self._clock(), "now")

    def _assert_no_overlap(
        self,
        resource_id: str,
        start: datetime,
        end: datetime,
        exclude_id: str | None = None,
    ) -> None:
        """Raise if an active booking for the resource overlaps ``[start, end)``.

        Intervals are half-open, so a booking ending exactly when another
        starts is not a conflict — back-to-back scheduling is allowed.
        """
        for existing in self._repository.list_for_resource(resource_id, start, end):
            if existing.id == exclude_id:
                continue
            raise BookingConflictError(
                f"Resource {resource_id!r} is already booked from "
                f"{existing.start_time.isoformat()} to {existing.end_time.isoformat()}."
            )
