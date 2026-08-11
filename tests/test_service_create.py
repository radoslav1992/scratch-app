"""Tests for creating bookings, especially overlap detection."""

from datetime import datetime, timedelta, timezone

import pytest

from booking import (
    BookingConflictError,
    BookingService,
    BookingStatus,
    BookingValidationError,
    InMemoryBookingRepository,
)

from .conftest import NOW, ONE_HOUR, TICK, slot


def test_valid_booking_is_created_and_stored(service, repo):
    booking = service.create_booking("user-1", "room-a", slot(10), slot(11))

    assert booking.id == "booking-1"
    assert booking.user_id == "user-1"
    assert booking.resource_id == "room-a"
    assert booking.start_time == slot(10)
    assert booking.end_time == slot(11)
    assert booking.status is BookingStatus.CONFIRMED
    assert repo.get("booking-1") == booking


def test_creation_still_enforces_the_time_only_rules(service):
    with pytest.raises(BookingValidationError, match="at least 24 hours"):
        service.create_booking("user-1", "room-a", NOW + ONE_HOUR, NOW + 2 * ONE_HOUR)


def test_naive_datetimes_are_accepted_and_stored_as_utc(service):
    booking = service.create_booking(
        "user-1", "room-a", slot(10).replace(tzinfo=None), slot(11).replace(tzinfo=None)
    )

    assert booking.start_time == slot(10)
    assert booking.start_time.tzinfo is timezone.utc


# --- Overlap: the half-open interval [start, end) ----------------------------


def test_back_to_back_bookings_are_allowed(service):
    """A booking ending exactly when the next begins is not a conflict."""
    first = service.create_booking("user-1", "room-a", slot(9), slot(10))
    second = service.create_booking("user-2", "room-a", slot(10), slot(11))

    assert first.end_time == second.start_time


def test_overlap_by_one_tick_is_rejected(service):
    service.create_booking("user-1", "room-a", slot(9), slot(10))

    with pytest.raises(BookingConflictError, match="already booked"):
        service.create_booking("user-2", "room-a", slot(10) - TICK, slot(11))


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ((10, 0), (11, 0)),
        ((9, 0), (12, 0)),
        ((10, 30), (11, 30)),
        ((9, 30), (10, 30)),
        ((10, 15), (10, 45)),
    ],
    ids=["identical", "contains", "overlaps-end", "overlaps-start", "contained-by"],
)
def test_overlapping_windows_are_rejected(service, start, end):
    service.create_booking("user-1", "room-a", slot(10), slot(11))

    with pytest.raises(BookingConflictError):
        service.create_booking("user-2", "room-a", slot(*start), slot(*end))


def test_same_window_on_a_different_resource_is_allowed(service):
    service.create_booking("user-1", "room-a", slot(10), slot(11))

    other = service.create_booking("user-2", "room-b", slot(10), slot(11))

    assert other.resource_id == "room-b"


def test_cancelled_booking_does_not_block_its_slot(service):
    first = service.create_booking("user-1", "room-a", slot(10), slot(11))
    service.cancel_booking(first.id)

    replacement = service.create_booking("user-2", "room-a", slot(10), slot(11))

    assert replacement.id != first.id


def test_conflicting_booking_is_not_stored(service, repo):
    service.create_booking("user-1", "room-a", slot(10), slot(11))

    with pytest.raises(BookingConflictError):
        service.create_booking("user-2", "room-a", slot(10), slot(11))

    assert len(repo.list_for_resource("room-a", slot(9), slot(17))) == 1


# --- The default clock -------------------------------------------------------


def test_lead_time_is_measured_against_the_real_clock_by_default():
    """Without an injected clock, validation uses the current UTC time."""
    service = BookingService(InMemoryBookingRepository())
    real_now = datetime.now(timezone.utc)
    tomorrow = (real_now + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)

    service.create_booking("user-1", "room-a", tomorrow, tomorrow + ONE_HOUR)

    with pytest.raises(BookingValidationError, match="at least 24 hours"):
        service.create_booking("user-1", "room-a", real_now + ONE_HOUR, real_now + 2 * ONE_HOUR)
