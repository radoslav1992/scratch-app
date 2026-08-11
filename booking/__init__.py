"""Booking domain: scheduling rules, storage, and lifecycle."""

from .errors import (
    BookingConflictError,
    BookingError,
    BookingNotFoundError,
    BookingStateError,
    BookingValidationError,
)
from .models import Booking, BookingStatus, as_utc
from .policy import (
    MINIMUM_LEAD_TIME,
    BookingPolicy,
    check_all,
    check_business_hours,
    check_duration,
    check_lead_time,
)
from .repository import BookingRepository, InMemoryBookingRepository
from .service import BookingService

__all__ = [
    "MINIMUM_LEAD_TIME",
    "Booking",
    "BookingConflictError",
    "BookingError",
    "BookingNotFoundError",
    "BookingPolicy",
    "BookingRepository",
    "BookingService",
    "BookingStateError",
    "BookingStatus",
    "BookingValidationError",
    "InMemoryBookingRepository",
    "as_utc",
    "check_all",
    "check_business_hours",
    "check_duration",
    "check_lead_time",
]
