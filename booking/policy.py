"""Scheduling rules that depend only on the booking's own times."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from .errors import BookingValidationError

UTC = ZoneInfo("UTC")

# Kept for backwards compatibility with the original module-level constant.
MINIMUM_LEAD_TIME = timedelta(hours=24)


@dataclass(frozen=True)
class BookingPolicy:
    """The tunable limits applied to every booking."""

    minimum_lead_time: timedelta = MINIMUM_LEAD_TIME
    maximum_duration: timedelta = timedelta(hours=8)
    opening_time: time = time(9, 0)
    closing_time: time = time(17, 0)
    timezone: ZoneInfo = UTC


def check_lead_time(start: datetime, now: datetime, policy: BookingPolicy) -> None:
    """Reject bookings starting sooner than the policy's lead time.

    The boundary is inclusive: starting exactly ``minimum_lead_time`` from now
    is allowed, since that is not *less than* the lead time.
    """
    if start - now < policy.minimum_lead_time:
        hours = policy.minimum_lead_time.total_seconds() / 3600
        raise BookingValidationError(
            f"Booking must start at least {hours:g} hours from now; "
            f"{start.isoformat()} is too soon (now is {now.isoformat()})."
        )


def check_duration(start: datetime, end: datetime, policy: BookingPolicy) -> None:
    """Reject bookings that do not end after they start, or that run too long."""
    if end <= start:
        raise BookingValidationError(
            "Booking end_time must be after start_time; "
            f"got start_time={start.isoformat()} and end_time={end.isoformat()}."
        )
    if end - start > policy.maximum_duration:
        hours = policy.maximum_duration.total_seconds() / 3600
        raise BookingValidationError(
            f"Booking may not run longer than {hours:g} hours; "
            f"got {(end - start).total_seconds() / 3600:g} hours."
        )


def check_business_hours(start: datetime, end: datetime, policy: BookingPolicy) -> None:
    """Reject bookings falling outside business hours or spanning a date change.

    Both edges are inclusive: starting exactly at opening time and ending
    exactly at closing time are both allowed.
    """
    local_start = start.astimezone(policy.timezone)
    local_end = end.astimezone(policy.timezone)

    if local_start.date() != local_end.date():
        raise BookingValidationError(
            "Booking may not span more than one day; "
            f"got {local_start.date()} to {local_end.date()}."
        )
    if local_start.time() < policy.opening_time:
        raise BookingValidationError(
            f"Booking may not start before {policy.opening_time:%H:%M}; "
            f"got {local_start:%H:%M} ({policy.timezone})."
        )
    if local_end.time() > policy.closing_time:
        raise BookingValidationError(
            f"Booking may not end after {policy.closing_time:%H:%M}; "
            f"got {local_end:%H:%M} ({policy.timezone})."
        )


def check_all(start: datetime, end: datetime, now: datetime, policy: BookingPolicy) -> None:
    """Run every time-only rule, in the order a caller would expect to hear about them."""
    check_lead_time(start, now, policy)
    check_duration(start, end, policy)
    check_business_hours(start, end, policy)
