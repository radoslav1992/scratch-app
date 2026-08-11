"""Tests for cancelling and rescheduling bookings."""

import pytest

from booking import (
    BookingConflictError,
    BookingNotFoundError,
    BookingStateError,
    BookingStatus,
    BookingValidationError,
)

from .conftest import NOW, ONE_HOUR, TICK, slot

# A moment after the day-3 bookings below have already begun.
AFTER_START = slot(10) + ONE_HOUR


# --- Queries -----------------------------------------------------------------


def test_get_booking_returns_the_stored_booking(service):
    created = service.create_booking("user-1", "room-a", slot(10), slot(11))

    assert service.get_booking(created.id) == created


def test_get_unknown_booking_raises(service):
    with pytest.raises(BookingNotFoundError, match="No booking with id"):
        service.get_booking("nope")


def test_list_bookings_for_user_is_ordered_and_includes_cancelled(service):
    late = service.create_booking("user-1", "room-a", slot(14), slot(15))
    early = service.create_booking("user-1", "room-a", slot(9), slot(10))
    service.create_booking("user-2", "room-a", slot(11), slot(12))
    service.cancel_booking(late.id)

    listed = service.list_bookings_for_user("user-1")

    assert [b.id for b in listed] == [early.id, late.id]
    assert listed[1].status is BookingStatus.CANCELLED


# --- Cancellation ------------------------------------------------------------


def test_cancel_marks_the_booking_cancelled(service):
    created = service.create_booking("user-1", "room-a", slot(10), slot(11))

    cancelled = service.cancel_booking(created.id)

    assert cancelled.status is BookingStatus.CANCELLED
    assert service.get_booking(created.id).status is BookingStatus.CANCELLED


def test_cancel_frees_the_slot(service):
    created = service.create_booking("user-1", "room-a", slot(10), slot(11))
    service.cancel_booking(created.id)

    service.create_booking("user-2", "room-a", slot(10), slot(11))


def test_cancelling_twice_raises(service):
    created = service.create_booking("user-1", "room-a", slot(10), slot(11))
    service.cancel_booking(created.id)

    with pytest.raises(BookingStateError, match="already cancelled"):
        service.cancel_booking(created.id)


def test_cancelling_an_unknown_booking_raises(service):
    with pytest.raises(BookingNotFoundError):
        service.cancel_booking("nope")


def test_a_booking_that_has_started_cannot_be_cancelled(make_service):
    service = make_service()
    created = service.create_booking("user-1", "room-a", slot(10), slot(11))

    # The clock moves past the booking's start; the same repository is shared.
    later = make_service(now=AFTER_START)

    with pytest.raises(BookingStateError, match="can no longer be cancelled"):
        later.cancel_booking(created.id)


def test_a_booking_can_be_cancelled_up_to_its_start(make_service):
    service = make_service()
    created = service.create_booking("user-1", "room-a", slot(10), slot(11))

    just_before = make_service(now=slot(10) - TICK)

    assert just_before.cancel_booking(created.id).status is BookingStatus.CANCELLED


# --- Rescheduling ------------------------------------------------------------


def test_reschedule_moves_the_booking(service):
    created = service.create_booking("user-1", "room-a", slot(10), slot(11))

    moved = service.reschedule_booking(created.id, slot(14), slot(15))

    assert moved.id == created.id
    assert (moved.start_time, moved.end_time) == (slot(14), slot(15))
    assert service.get_booking(created.id).start_time == slot(14)


def test_reschedule_within_its_own_window_succeeds(service):
    """The booking must not be treated as a conflict with itself."""
    created = service.create_booking("user-1", "room-a", slot(10), slot(11))

    moved = service.reschedule_booking(created.id, slot(10, 30), slot(11, 30))

    assert moved.start_time == slot(10, 30)


def test_reschedule_onto_another_booking_is_rejected(service):
    service.create_booking("user-1", "room-a", slot(14), slot(15))
    created = service.create_booking("user-2", "room-a", slot(10), slot(11))

    with pytest.raises(BookingConflictError, match="already booked"):
        service.reschedule_booking(created.id, slot(14), slot(15))


def test_reschedule_leaves_the_booking_untouched_when_rejected(service):
    service.create_booking("user-1", "room-a", slot(14), slot(15))
    created = service.create_booking("user-2", "room-a", slot(10), slot(11))

    with pytest.raises(BookingConflictError):
        service.reschedule_booking(created.id, slot(14), slot(15))

    assert service.get_booking(created.id).start_time == slot(10)


def test_reschedule_to_a_back_to_back_slot_is_allowed(service):
    service.create_booking("user-1", "room-a", slot(14), slot(15))
    created = service.create_booking("user-2", "room-a", slot(10), slot(11))

    moved = service.reschedule_booking(created.id, slot(13), slot(14))

    assert moved.end_time == slot(14)


def test_reschedule_still_enforces_the_lead_time(service):
    """Lead time is measured from now, so a booking cannot be dragged forward."""
    created = service.create_booking("user-1", "room-a", slot(10), slot(11))

    with pytest.raises(BookingValidationError, match="at least 24 hours"):
        service.reschedule_booking(created.id, NOW + ONE_HOUR, NOW + 2 * ONE_HOUR)


def test_reschedule_still_enforces_business_hours(service):
    created = service.create_booking("user-1", "room-a", slot(10), slot(11))

    with pytest.raises(BookingValidationError, match="may not end after 17:00"):
        service.reschedule_booking(created.id, slot(16), slot(18))


def test_reschedule_still_enforces_duration(service):
    created = service.create_booking("user-1", "room-a", slot(10), slot(11))

    with pytest.raises(BookingValidationError, match="after start_time"):
        service.reschedule_booking(created.id, slot(11), slot(11))


def test_rescheduling_a_cancelled_booking_raises(service):
    created = service.create_booking("user-1", "room-a", slot(10), slot(11))
    service.cancel_booking(created.id)

    with pytest.raises(BookingStateError, match="cancelled and cannot be moved"):
        service.reschedule_booking(created.id, slot(14), slot(15))


def test_rescheduling_an_unknown_booking_raises(service):
    with pytest.raises(BookingNotFoundError):
        service.reschedule_booking("nope", slot(14), slot(15))
