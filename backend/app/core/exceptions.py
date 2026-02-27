"""
Custom Exception Hierarchy — Single Responsibility Principle (SRP)
Each exception has a single, clear purpose.
"""
from fastapi import HTTPException, status
from typing import Union


class GenXSOPException(Exception):
    """Base exception for all GenXSOP domain errors."""
    def __init__(self, message: str, code: str = "GENXSOP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


# ── 404 Not Found ────────────────────────────────────────────────────────────

class EntityNotFoundException(GenXSOPException):
    """Raised when a requested entity does not exist in the database."""
    def __init__(self, entity: str, entity_id: Union[int, str]):
        super().__init__(
            message=f"{entity} with id '{entity_id}' not found.",
            code="NOT_FOUND",
        )
        self.entity = entity
        self.entity_id = entity_id


# ── 400 Bad Request / Business Rule Violations ───────────────────────────────

class BusinessRuleViolationException(GenXSOPException):
    """Raised when a business rule is violated (e.g., modifying a locked plan)."""
    def __init__(self, message: str):
        super().__init__(message=message, code="BUSINESS_RULE_VIOLATION")


class DuplicateEntityException(GenXSOPException):
    """Raised when a unique constraint would be violated."""
    def __init__(self, entity: str, field: str, value: str):
        super().__init__(
            message=f"{entity} with {field}='{value}' already exists.",
            code="DUPLICATE_ENTITY",
        )


class InvalidStateTransitionException(GenXSOPException):
    """Raised when an entity cannot transition to the requested state."""
    def __init__(self, entity: str, current_state: str, target_state: str):
        super().__init__(
            message=f"Cannot transition {entity} from '{current_state}' to '{target_state}'.",
            code="INVALID_STATE_TRANSITION",
        )


# ── 403 Forbidden ────────────────────────────────────────────────────────────

class InsufficientPermissionsException(GenXSOPException):
    """Raised when a user lacks the required role/permission."""
    def __init__(self, required_roles: list[str]):
        super().__init__(
            message=f"Access denied. Required roles: {required_roles}",
            code="INSUFFICIENT_PERMISSIONS",
        )


# ── 401 Unauthorized ─────────────────────────────────────────────────────────

class AuthenticationException(GenXSOPException):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication failed."):
        super().__init__(message=message, code="AUTHENTICATION_FAILED")


# ── 500 Internal / ML Errors ─────────────────────────────────────────────────

class ForecastGenerationException(GenXSOPException):
    """Raised when ML forecast generation fails."""
    def __init__(self, product_id: int, model: str, reason: str):
        super().__init__(
            message=f"Forecast generation failed for product {product_id} using model '{model}': {reason}",
            code="FORECAST_GENERATION_FAILED",
        )


class InsufficientDataException(GenXSOPException):
    """Raised when there is not enough historical data for an operation."""
    def __init__(self, required: int, available: int, operation: str = "operation"):
        super().__init__(
            message=f"Insufficient data for {operation}: requires {required} records, found {available}.",
            code="INSUFFICIENT_DATA",
        )


# ── FastAPI Exception Handlers ───────────────────────────────────────────────

def to_http_exception(exc: GenXSOPException) -> HTTPException:
    """
    Adapter: converts domain exceptions to FastAPI HTTPExceptions.
    Open/Closed Principle — add new mappings without modifying existing ones.
    """
    mapping = {
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "DUPLICATE_ENTITY": status.HTTP_400_BAD_REQUEST,
        "BUSINESS_RULE_VIOLATION": status.HTTP_400_BAD_REQUEST,
        "INVALID_STATE_TRANSITION": status.HTTP_400_BAD_REQUEST,
        "INSUFFICIENT_PERMISSIONS": status.HTTP_403_FORBIDDEN,
        "AUTHENTICATION_FAILED": status.HTTP_401_UNAUTHORIZED,
        "FORECAST_GENERATION_FAILED": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INSUFFICIENT_DATA": status.HTTP_422_UNPROCESSABLE_ENTITY,
    }
    status_code = mapping.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message})
