"""Booking creation with scheduling validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# A booking may not start any sooner than this from the moment it is created.
MINIMUM_LEAD_TIME = timedelta(hours=24)


class BookingValidationError(ValueError):
    """Raised when a booking violates a scheduling rule."""


@dataclass(frozen=True)
class Booking:
    """A confirmed booking. Times are always stored in UTC."""

    user_id: str
    start_time: datetime
    end_time: datetime


def _as_utc(value: object, field: str) -> datetime:
    """Normalise a datetime to UTC. Naive datetimes are assumed to be UTC."""
    if not isinstance(value, datetime):
        raise BookingValidationError(f"{field} must be a datetime, got {type(value).__name__}")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_booking(
    user_id: str,
    start_time: datetime,
    end_time: datetime,
    now: datetime | None = None,
) -> Booking:
    """Create a booking after checking it against the scheduling rules.

    Args:
        user_id: Owner of the booking.
        start_time: When the booking starts.
        end_time: When the booking ends; must be strictly after ``start_time``.
        now: Reference point for the lead-time check. Defaults to the current
            UTC time; injectable so callers (and tests) can pin it.

    Returns:
        The created :class:`Booking`, with both times normalised to UTC.

    Raises:
        BookingValidationError: If the booking starts less than 24 hours from
            ``now``, or if ``end_time`` is not after ``start_time``.
    """
    start = _as_utc(start_time, "start_time")
    end = _as_utc(end_time, "end_time")
    reference = _as_utc(now, "now") if now is not None else datetime.now(timezone.utc)

    if start - reference < MINIMUM_LEAD_TIME:
        raise BookingValidationError(
            "Booking must start at least 24 hours from now; "
            f"{start.isoformat()} is too soon (now is {reference.isoformat()})."
        )

    if end <= start:
        raise BookingValidationError(
            "Booking end_time must be after start_time; "
            f"got start_time={start.isoformat()} and end_time={end.isoformat()}."
        )

    return Booking(user_id=user_id, start_time=start, end_time=end)
