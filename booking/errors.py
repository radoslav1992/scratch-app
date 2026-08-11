"""Exceptions raised by the booking domain."""

from __future__ import annotations


class BookingError(Exception):
    """Base class for every booking failure, so callers can catch broadly."""


class BookingValidationError(BookingError, ValueError):
    """A booking violates a scheduling rule.

    Also a :class:`ValueError` so that callers written against the original
    module-level ``create_booking`` keep working.
    """


class BookingNotFoundError(BookingError):
    """No booking exists with the requested id."""


class BookingConflictError(BookingError):
    """The requested window overlaps an existing booking for the same resource."""


class BookingStateError(BookingError):
    """The booking's current status does not allow the requested transition."""
