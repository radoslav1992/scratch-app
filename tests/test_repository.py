"""Tests for the in-memory booking repository."""

import dataclasses

from booking import Booking, BookingStatus

from .conftest import slot


def make_booking(booking_id="b1", user_id="user-1", resource_id="room-a", start=9, end=10):
    return Booking(booking_id, user_id, resource_id, slot(start), slot(end))


def test_add_and_get_round_trip(repo):
    booking = make_booking()
    repo.add(booking)

    assert repo.get("b1") == booking


def test_get_unknown_id_returns_none(repo):
    assert repo.get("nope") is None


def test_update_replaces_in_place(repo):
    repo.add(make_booking())
    cancelled = dataclasses.replace(repo.get("b1"), status=BookingStatus.CANCELLED)

    repo.update(cancelled)

    assert repo.get("b1").status is BookingStatus.CANCELLED
    assert len(repo.list_for_user("user-1")) == 1


def test_list_for_resource_filters_by_resource(repo):
    repo.add(make_booking("b1", resource_id="room-a"))
    repo.add(make_booking("b2", resource_id="room-b"))

    found = repo.list_for_resource("room-a", slot(9), slot(10))

    assert [b.id for b in found] == ["b1"]


def test_list_for_resource_excludes_cancelled(repo):
    repo.add(dataclasses.replace(make_booking(), status=BookingStatus.CANCELLED))

    assert repo.list_for_resource("room-a", slot(9), slot(10)) == []


def test_list_for_resource_uses_half_open_windows(repo):
    repo.add(make_booking("b1", start=9, end=10))

    # Windows that merely touch the booking's edges do not intersect it.
    assert repo.list_for_resource("room-a", slot(10), slot(11)) == []
    assert repo.list_for_resource("room-a", slot(8), slot(9)) == []
    # Any genuine overlap does.
    assert len(repo.list_for_resource("room-a", slot(9), slot(11))) == 1


def test_list_for_resource_is_ordered_by_start_time(repo):
    repo.add(make_booking("late", start=14, end=15))
    repo.add(make_booking("early", start=9, end=10))

    found = repo.list_for_resource("room-a", slot(9), slot(16))

    assert [b.id for b in found] == ["early", "late"]


def test_list_for_user_includes_cancelled(repo):
    repo.add(make_booking("b1", user_id="user-1"))
    repo.add(
        dataclasses.replace(
            make_booking("b2", user_id="user-1", start=14, end=15),
            status=BookingStatus.CANCELLED,
        )
    )
    repo.add(make_booking("b3", user_id="user-2"))

    assert [b.id for b in repo.list_for_user("user-1")] == ["b1", "b2"]
