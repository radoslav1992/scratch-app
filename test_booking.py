"""Tests for booking validation rules."""

from datetime import datetime, timedelta, timezone

import pytest

from booking import MINIMUM_LEAD_TIME, Booking, BookingValidationError, create_booking

NOW = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
ONE_HOUR = timedelta(hours=1)
TICK = timedelta(microseconds=1)


def test_valid_booking_is_created():
    start = NOW + timedelta(days=3)
    booking = create_booking("user-1", start, start + ONE_HOUR, now=NOW)

    assert booking == Booking("user-1", start, start + ONE_HOUR)


# --- Rule: a booking may not start less than 24 hours from now ---------------


def test_start_exactly_at_lead_time_is_allowed():
    """The boundary itself is valid: 24 hours out is not *less than* 24 hours."""
    start = NOW + MINIMUM_LEAD_TIME
    booking = create_booking("user-1", start, start + ONE_HOUR, now=NOW)

    assert booking.start_time == start


def test_start_just_inside_lead_time_is_rejected():
    start = NOW + MINIMUM_LEAD_TIME - TICK

    with pytest.raises(BookingValidationError, match="at least 24 hours"):
        create_booking("user-1", start, start + ONE_HOUR, now=NOW)


def test_start_just_outside_lead_time_is_allowed():
    start = NOW + MINIMUM_LEAD_TIME + TICK
    booking = create_booking("user-1", start, start + ONE_HOUR, now=NOW)

    assert booking.start_time == start


@pytest.mark.parametrize(
    "offset",
    [timedelta(0), ONE_HOUR, timedelta(hours=23, minutes=59), -ONE_HOUR, -timedelta(days=7)],
    ids=["now", "one-hour-out", "just-under-a-day", "one-hour-ago", "a-week-ago"],
)
def test_start_inside_lead_time_or_in_the_past_is_rejected(offset):
    start = NOW + offset

    with pytest.raises(BookingValidationError, match="at least 24 hours"):
        create_booking("user-1", start, start + ONE_HOUR, now=NOW)


# --- Rule: end_time must be strictly after start_time ------------------------


def test_end_equal_to_start_is_rejected():
    """The boundary itself is invalid: a zero-length booking is not allowed."""
    start = NOW + timedelta(days=3)

    with pytest.raises(BookingValidationError, match="after start_time"):
        create_booking("user-1", start, start, now=NOW)


def test_end_one_tick_after_start_is_allowed():
    start = NOW + timedelta(days=3)
    booking = create_booking("user-1", start, start + TICK, now=NOW)

    assert booking.end_time == start + TICK


def test_end_one_tick_before_start_is_rejected():
    start = NOW + timedelta(days=3)

    with pytest.raises(BookingValidationError, match="after start_time"):
        create_booking("user-1", start, start - TICK, now=NOW)


def test_end_well_before_start_is_rejected():
    start = NOW + timedelta(days=3)

    with pytest.raises(BookingValidationError, match="after start_time"):
        create_booking("user-1", start, start - timedelta(days=1), now=NOW)


# --- Interaction and normalisation ------------------------------------------


def test_booking_violating_both_rules_is_rejected():
    start = NOW + ONE_HOUR

    with pytest.raises(BookingValidationError):
        create_booking("user-1", start, start - ONE_HOUR, now=NOW)


def test_naive_datetimes_are_treated_as_utc():
    start = (NOW + timedelta(days=3)).replace(tzinfo=None)
    booking = create_booking("user-1", start, start + ONE_HOUR, now=NOW)

    assert booking.start_time == NOW + timedelta(days=3)
    assert booking.start_time.tzinfo is timezone.utc


def test_times_in_other_offsets_are_normalised_to_utc():
    plus_two = timezone(timedelta(hours=2))
    start = (NOW + timedelta(days=3)).astimezone(plus_two)
    booking = create_booking("user-1", start, start + ONE_HOUR, now=NOW)

    assert booking.start_time == NOW + timedelta(days=3)
    assert booking.start_time.utcoffset() == timedelta(0)


def test_lead_time_is_measured_against_the_real_clock_by_default():
    """Without an injected ``now``, validation uses the current UTC time."""
    real_now = datetime.now(timezone.utc)

    create_booking("user-1", real_now + timedelta(days=2), real_now + timedelta(days=2, hours=1))

    with pytest.raises(BookingValidationError, match="at least 24 hours"):
        create_booking("user-1", real_now + ONE_HOUR, real_now + timedelta(hours=2))


@pytest.mark.parametrize("bad", ["2026-08-14T12:00:00", None, 0], ids=["str", "none", "int"])
def test_non_datetime_inputs_are_rejected(bad):
    start = NOW + timedelta(days=3)

    with pytest.raises(BookingValidationError, match="must be a datetime"):
        create_booking("user-1", bad, start + ONE_HOUR, now=NOW)
