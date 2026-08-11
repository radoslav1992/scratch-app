"""Tests for the time-only scheduling rules."""

from datetime import time, timedelta

import pytest

from booking import (
    MINIMUM_LEAD_TIME,
    BookingPolicy,
    BookingValidationError,
    check_all,
    check_business_hours,
    check_duration,
    check_lead_time,
)

from .conftest import NOW, ONE_HOUR, TICK, slot

POLICY = BookingPolicy()


# --- Rule: a booking may not start less than 24 hours from now ---------------


def test_start_exactly_at_lead_time_is_allowed():
    """The boundary itself is valid: 24 hours out is not *less than* 24 hours."""
    check_lead_time(NOW + MINIMUM_LEAD_TIME, NOW, POLICY)


def test_start_just_inside_lead_time_is_rejected():
    with pytest.raises(BookingValidationError, match="at least 24 hours"):
        check_lead_time(NOW + MINIMUM_LEAD_TIME - TICK, NOW, POLICY)


def test_start_just_outside_lead_time_is_allowed():
    check_lead_time(NOW + MINIMUM_LEAD_TIME + TICK, NOW, POLICY)


@pytest.mark.parametrize(
    "offset",
    [timedelta(0), ONE_HOUR, timedelta(hours=23, minutes=59), -ONE_HOUR, -timedelta(days=7)],
    ids=["now", "one-hour-out", "just-under-a-day", "one-hour-ago", "a-week-ago"],
)
def test_start_inside_lead_time_or_in_the_past_is_rejected(offset):
    with pytest.raises(BookingValidationError, match="at least 24 hours"):
        check_lead_time(NOW + offset, NOW, POLICY)


def test_lead_time_is_configurable():
    policy = BookingPolicy(minimum_lead_time=ONE_HOUR)

    check_lead_time(NOW + ONE_HOUR, NOW, policy)
    with pytest.raises(BookingValidationError, match="at least 1 hours"):
        check_lead_time(NOW + ONE_HOUR - TICK, NOW, policy)


# --- Rule: end_time must be strictly after start_time ------------------------


def test_end_equal_to_start_is_rejected():
    """The boundary itself is invalid: a zero-length booking is not allowed."""
    with pytest.raises(BookingValidationError, match="after start_time"):
        check_duration(slot(10), slot(10), POLICY)


def test_end_one_tick_after_start_is_allowed():
    check_duration(slot(10), slot(10) + TICK, POLICY)


def test_end_one_tick_before_start_is_rejected():
    with pytest.raises(BookingValidationError, match="after start_time"):
        check_duration(slot(10), slot(10) - TICK, POLICY)


def test_end_well_before_start_is_rejected():
    with pytest.raises(BookingValidationError, match="after start_time"):
        check_duration(slot(10), slot(10) - timedelta(days=1), POLICY)


# --- Rule: a booking may not run longer than the maximum duration ------------


def test_duration_exactly_at_maximum_is_allowed():
    check_duration(slot(9), slot(9) + POLICY.maximum_duration, POLICY)


def test_duration_one_tick_over_maximum_is_rejected():
    with pytest.raises(BookingValidationError, match="may not run longer than 8 hours"):
        check_duration(slot(9), slot(9) + POLICY.maximum_duration + TICK, POLICY)


# --- Rule: bookings fall inside business hours, on a single day --------------


def test_booking_spanning_full_business_day_is_allowed():
    """Both edges are inclusive: open exactly at 09:00, close exactly at 17:00."""
    check_business_hours(slot(9), slot(17), POLICY)


def test_start_one_tick_before_opening_is_rejected():
    with pytest.raises(BookingValidationError, match="may not start before 09:00"):
        check_business_hours(slot(9) - TICK, slot(10), POLICY)


def test_end_one_tick_after_closing_is_rejected():
    with pytest.raises(BookingValidationError, match="may not end after 17:00"):
        check_business_hours(slot(16), slot(17) + TICK, POLICY)


def test_booking_spanning_midnight_is_rejected():
    policy = BookingPolicy(opening_time=time(0, 0), closing_time=time(23, 59))

    with pytest.raises(BookingValidationError, match="may not span more than one day"):
        check_business_hours(slot(23), slot(1, days=4), policy)


def test_business_hours_are_evaluated_in_the_policy_timezone():
    from zoneinfo import ZoneInfo

    # 13:00 UTC is 09:00 in New York — inside hours there, and the equivalent
    # UTC-hours policy would place the same instant outside its own morning.
    policy = BookingPolicy(timezone=ZoneInfo("America/New_York"))

    check_business_hours(slot(13), slot(14), policy)
    with pytest.raises(BookingValidationError, match="may not start before 09:00"):
        check_business_hours(slot(12), slot(13), policy)


# --- The rules applied together ---------------------------------------------


def test_check_all_accepts_a_valid_window():
    check_all(slot(10), slot(11), NOW, POLICY)


def test_check_all_reports_the_lead_time_first():
    """A booking breaking several rules names the soonest problem."""
    with pytest.raises(BookingValidationError, match="at least 24 hours"):
        check_all(NOW + ONE_HOUR, NOW, NOW, POLICY)
