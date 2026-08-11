"""Booking creation and validation."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

MINIMUM_LEAD_TIME = timedelta(hours=24)


class BookingValidationError(ValueError):
    """Raised when a booking violates a scheduling rule."""


@dataclass(frozen=True)
class Booking:
    customer: str
    start: datetime
    end: datetime


def _as_utc(value, label):
    """Normalize a datetime to UTC, treating naive values as UTC."""
    if not isinstance(value, datetime):
        raise BookingValidationError(f"{label} must be a datetime, got {type(value).__name__}")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_booking(customer, start, end, now=None):
    """Create a booking after validating its schedule.

    A booking must start at least 24 hours from now and must end strictly
    after it starts. ``now`` is injectable so callers (and tests) can pin the
    reference time; it defaults to the current UTC time.
    """
    start = _as_utc(start, "start")
    end = _as_utc(end, "end")
    now = datetime.now(timezone.utc) if now is None else _as_utc(now, "now")

    if start - now < MINIMUM_LEAD_TIME:
        raise BookingValidationError(
            f"booking must start at least 24 hours from now; "
            f"start {start.isoformat()} is only {start - now} after {now.isoformat()}"
        )

    if end <= start:
        raise BookingValidationError(
            f"booking end {end.isoformat()} must be after start {start.isoformat()}"
        )

    return Booking(customer=customer, start=start, end=end)
