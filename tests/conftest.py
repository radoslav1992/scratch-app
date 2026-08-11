"""Shared fixtures. Time and ids are pinned so every test is deterministic."""

import itertools
from datetime import datetime, timedelta, timezone

import pytest

from booking import BookingPolicy, BookingService, InMemoryBookingRepository

NOW = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
ONE_HOUR = timedelta(hours=1)
TICK = timedelta(microseconds=1)


def slot(hour, minute=0, *, days=3):
    """A time on a day comfortably beyond the 24-hour lead time."""
    return (NOW + timedelta(days=days)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )


@pytest.fixture
def repo():
    return InMemoryBookingRepository()


@pytest.fixture
def make_service(repo):
    """Build services sharing one repository, one id sequence, and a fixed clock.

    Pass ``now`` to simulate the clock having moved on — the only way to reach
    states (such as a booking that has already started) that the lead-time rule
    prevents from being created directly.
    """
    counter = itertools.count(1)

    def _make(now=NOW, policy=None, repository=None):
        return BookingService(
            repository if repository is not None else repo,
            policy=policy or BookingPolicy(),
            clock=lambda: now,
            id_factory=lambda: f"booking-{next(counter)}",
        )

    return _make


@pytest.fixture
def service(make_service):
    return make_service()
