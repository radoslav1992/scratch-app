"""Booking domain types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum

from .errors import BookingValidationError


class BookingStatus(StrEnum):
    """Lifecycle state of a booking."""

    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Booking:
    """A booking. Times are always stored in UTC.

    Frozen, so lifecycle transitions go through :func:`dataclasses.replace`
    rather than mutating in place.
    """

    id: str
    user_id: str
    resource_id: str
    start_time: datetime
    end_time: datetime
    status: BookingStatus = BookingStatus.CONFIRMED

    @property
    def is_active(self) -> bool:
        return self.status is BookingStatus.CONFIRMED


def as_utc(value: object, field: str) -> datetime:
    """Normalise a datetime to UTC. Naive datetimes are assumed to be UTC."""
    if not isinstance(value, datetime):
        raise BookingValidationError(f"{field} must be a datetime, got {type(value).__name__}")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
