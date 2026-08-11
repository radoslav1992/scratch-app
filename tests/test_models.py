"""Tests for the domain types and UTC normalisation."""

from datetime import timedelta, timezone

import pytest

from booking import Booking, BookingStatus, BookingValidationError, as_utc

from .conftest import NOW, ONE_HOUR, slot


def test_naive_datetimes_are_treated_as_utc():
    naive = slot(10).replace(tzinfo=None)

    assert as_utc(naive, "start_time") == slot(10)
    assert as_utc(naive, "start_time").tzinfo is timezone.utc


def test_times_in_other_offsets_are_normalised_to_utc():
    plus_two = timezone(timedelta(hours=2))
    shifted = slot(10).astimezone(plus_two)

    normalised = as_utc(shifted, "start_time")

    assert normalised == slot(10)
    assert normalised.utcoffset() == timedelta(0)


def test_utc_datetimes_pass_through_unchanged():
    assert as_utc(NOW, "start_time") == NOW


@pytest.mark.parametrize("bad", ["2026-08-14T12:00:00", None, 0], ids=["str", "none", "int"])
def test_non_datetime_inputs_are_rejected(bad):
    with pytest.raises(BookingValidationError, match="must be a datetime"):
        as_utc(bad, "start_time")


def test_validation_error_is_still_a_value_error():
    """Callers written against the original create_booking caught ValueError."""
    assert issubclass(BookingValidationError, ValueError)


def test_new_bookings_are_confirmed_and_active():
    booking = Booking("b1", "user-1", "room-a", slot(10), slot(10) + ONE_HOUR)

    assert booking.status is BookingStatus.CONFIRMED
    assert booking.is_active


def test_cancelled_bookings_are_not_active():
    booking = Booking(
        "b1", "user-1", "room-a", slot(10), slot(10) + ONE_HOUR, BookingStatus.CANCELLED
    )

    assert not booking.is_active
