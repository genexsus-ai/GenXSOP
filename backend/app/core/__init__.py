# Core module: exceptions, base classes, interfaces
from app.core.exceptions import (
    GenXSOPException,
    EntityNotFoundException,
    BusinessRuleViolationException,
    DuplicateEntityException,
    InvalidStateTransitionException,
    InsufficientPermissionsException,
    AuthenticationException,
    ForecastGenerationException,
    InsufficientDataException,
    to_http_exception,
)

__all__ = [
    "GenXSOPException",
    "EntityNotFoundException",
    "BusinessRuleViolationException",
    "DuplicateEntityException",
    "InvalidStateTransitionException",
    "InsufficientPermissionsException",
    "AuthenticationException",
    "ForecastGenerationException",
    "InsufficientDataException",
    "to_http_exception",
]
