"""
Centralized exception handling for the RAG backend.
"""
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Union, Dict, Any
import logging
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)


class APIError(HTTPException):
    """Base API error with consistent structure"""

    def __init__(self, status_code: int, detail: str, error_type: str = "api_error", **kwargs):
        super().__init__(status_code=status_code, detail=detail)
        self.error_type = error_type
        self.timestamp = datetime.utcnow().isoformat()
        self.extra_data = kwargs


class InvestigationError(APIError):
    """Investigation-specific errors"""

    def __init__(self, detail: str, investigation_id: str = None, **kwargs):
        super().__init__(
            status_code=500,
            detail=detail,
            error_type="investigation_error",
            investigation_id=investigation_id,
            **kwargs
        )


class AlertError(APIError):
    """Alert-specific errors"""

    def __init__(self, detail: str, alert_id: str = None, **kwargs):
        super().__init__(
            status_code=500,
            detail=detail,
            error_type="alert_error",
            alert_id=alert_id,
            **kwargs
        )


class AuthenticationError(APIError):
    """Authentication-specific errors"""

    def __init__(self, detail: str = "Authentication failed", **kwargs):
        super().__init__(
            status_code=401,
            detail=detail,
            error_type="authentication_error",
            **kwargs
        )


class DatabaseError(APIError):
    """Database-specific errors"""

    def __init__(self, detail: str, operation: str = None, **kwargs):
        super().__init__(
            status_code=500,
            detail=detail,
            error_type="database_error",
            operation=operation,
            **kwargs
        )


# Global exception handlers
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle custom API errors with consistent format"""

    # Log the error
    logger.error(
        f"API Error: {exc.error_type} - {exc.detail}",
        extra={
            "error_type": exc.error_type,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "user_agent": request.headers.get("user-agent"),
            **exc.extra_data
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": exc.error_type,
                "message": exc.detail,
                "timestamp": exc.timestamp,
                "path": request.url.path,
                **exc.extra_data
            }
        }
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors with detailed field information"""

    logger.warning(
        f"Validation Error: {exc.errors()}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors()
        }
    )

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "validation_error",
                "message": "Invalid input data",
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path,
                "details": exc.errors()
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other exceptions with secure error disclosure"""

    # Log full exception details
    logger.error(
        f"Unhandled Exception: {type(exc).__name__} - {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc()
        }
    )

    # Return generic error to user (don't expose internal details)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "internal_server_error",
                "message": "An unexpected error occurred",
                "timestamp": datetime.utcnow().isoformat(),
                "path": request.url.path,
                "reference": f"ERR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            }
        }
    )


# Context managers for error handling
class ErrorContext:
    """Context manager for consistent error handling"""

    def __init__(self, operation: str, **context):
        self.operation = operation
        self.context = context

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(
                f"Error in {self.operation}: {exc_val}",
                extra={
                    "operation": self.operation,
                    "exception_type": exc_type.__name__,
                    **self.context
                }
            )
        return False  # Don't suppress exceptions


# Decorators for endpoint error handling
def handle_errors(error_type: str = "api_error"):
    """Decorator for endpoint error handling"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise  # Re-raise HTTP exceptions
            except Exception as e:
                logger.error(
                    f"Error in {func.__name__}: {str(e)}",
                    extra={
                        "function": func.__name__,
                        "error_type": error_type,
                        "args": str(args),
                        "kwargs": str(kwargs)
                    },
                    exc_info=True
                )
                raise APIError(
                    status_code=500,
                    detail=f"Operation failed: {str(e)}",
                    error_type=error_type,
                    function=func.__name__
                )
        return wrapper
    return decorator
