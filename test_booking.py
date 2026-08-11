from datetime import datetime, timedelta, timezone

import pytest

from booking import MINIMUM_LEAD_TIME, Booking, BookingValidationError, create_booking

NOW = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
TICK = timedelta(microseconds=1)


def test_valid_booking_is_created():
    start = NOW + timedelta(days=3)
    end = start + timedelta(hours=2)

    booking = create_booking("ada", start, end, now=NOW)

    assert booking == Booking(customer="ada", start=start, end=end)


# --- 24-hour lead time rule ---


def test_rejects_booking_starting_less_than_24_hours_out():
    start = NOW + timedelta(hours=5)

    with pytest.raises(BookingValidationError, match="at least 24 hours"):
        create_booking("ada", start, start + timedelta(hours=1), now=NOW)


def test_rejects_booking_starting_in_the_past():
    start = NOW - timedelta(days=1)

    with pytest.raises(BookingValidationError, match="at least 24 hours"):
        create_booking("ada", start, start + timedelta(hours=1), now=NOW)


def test_accepts_booking_starting_exactly_24_hours_out():
    """Boundary: exactly 24 hours is allowed; only *less than* 24 is rejected."""
    start = NOW + MINIMUM_LEAD_TIME

    booking = create_booking("ada", start, start + timedelta(hours=1), now=NOW)

    assert booking.start == start


def test_rejects_booking_one_tick_under_24_hours():
    """Boundary: the smallest possible shortfall still fails."""
    start = NOW + MINIMUM_LEAD_TIME - TICK

    with pytest.raises(BookingValidationError, match="at least 24 hours"):
        create_booking("ada", start, start + timedelta(hours=1), now=NOW)


def test_accepts_booking_one_tick_over_24_hours():
    start = NOW + MINIMUM_LEAD_TIME + TICK

    assert create_booking("ada", start, start + timedelta(hours=1), now=NOW).start == start


# --- end-after-start rule ---


def test_rejects_end_before_start():
    start = NOW + timedelta(days=2)

    with pytest.raises(BookingValidationError, match="must be after start"):
        create_booking("ada", start, start - timedelta(hours=1), now=NOW)


def test_rejects_end_equal_to_start():
    """Boundary: a zero-length booking is not 'after' its start."""
    start = NOW + timedelta(days=2)

    with pytest.raises(BookingValidationError, match="must be after start"):
        create_booking("ada", start, start, now=NOW)


def test_accepts_end_one_tick_after_start():
    """Boundary: the shortest possible non-empty booking is allowed."""
    start = NOW + timedelta(days=2)
    end = start + TICK

    assert create_booking("ada", start, end, now=NOW).end == end


# --- rule interaction and time handling ---


def test_lead_time_is_checked_before_end_time():
    """A booking breaking both rules reports the lead-time failure."""
    start = NOW + timedelta(hours=1)

    with pytest.raises(BookingValidationError, match="at least 24 hours"):
        create_booking("ada", start, start - timedelta(hours=1), now=NOW)


def test_naive_datetimes_are_treated_as_utc():
    start = (NOW + timedelta(days=2)).replace(tzinfo=None)
    end = start + timedelta(hours=1)

    booking = create_booking("ada", start, end, now=NOW)

    assert booking.start == NOW + timedelta(days=2)
    assert booking.start.tzinfo is timezone.utc


def test_mixed_timezones_compare_by_absolute_time():
    """A start 23h out in another zone is still under the lead time."""
    other_zone = timezone(timedelta(hours=9))
    start = (NOW + timedelta(hours=23)).astimezone(other_zone)

    with pytest.raises(BookingValidationError, match="at least 24 hours"):
        create_booking("ada", start, start + timedelta(hours=1), now=NOW)


def test_now_defaults_to_current_time():
    start = datetime.now(timezone.utc) + timedelta(hours=1)

    with pytest.raises(BookingValidationError, match="at least 24 hours"):
        create_booking("ada", start, start + timedelta(hours=1))


def test_non_datetime_start_is_rejected():
    with pytest.raises(BookingValidationError, match="start must be a datetime"):
        create_booking("ada", "2026-08-20T12:00:00", NOW + timedelta(days=10), now=NOW)
