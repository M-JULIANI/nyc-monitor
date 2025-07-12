"""
Streamlined middleware configuration for the RAG backend.
Only the essentials: CORS, rate limiting, and optional simple logging.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
import logging
from typing import Dict, Any
from datetime import datetime
import uuid

from .config import get_config

logger = logging.getLogger(__name__)


class SimpleRequestLoggingMiddleware(BaseHTTPMiddleware):
    """Simple request logging with request ID tracking"""

    async def dispatch(self, request: Request, call_next):
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Simple logging - only for non-health endpoints that take > 1 second
        if request.url.path not in ["/health", "/docs", "/openapi.json"] and duration > 1.0:
            logger.info(
                f"Request {request_id}: {request.method} {request.url.path} -> {response.status_code} ({duration:.3f}s)"
            )

        # Add request ID to response headers for debugging
        response.headers["X-Request-ID"] = request_id

        return response


def configure_middleware(app: FastAPI) -> None:
    """Configure only the essential middleware"""

    config = get_config()

    # 1. CORS Middleware (essential for your frontend)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_allowed_origins(config),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
        max_age=3600  # Cache preflight requests
    )

    # 2. Simple Request Logging (optional - set ENABLE_REQUEST_LOGGING=true to enable)
    if getattr(config, 'ENABLE_REQUEST_LOGGING', False):
        app.add_middleware(SimpleRequestLoggingMiddleware)

    # 3. Rate Limiting (keep your existing setup)
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    logger.info("✅ Essential middleware configured successfully")


def get_allowed_origins(config) -> list:
    """Get allowed origins based on environment"""

    base_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ]

    if config.ENV == "production":
        base_origins.extend([
            "https://nyc-monitor.app",
            "https://atlas-frontend-290750569862.us-central1.run.app",
        ])

    return base_origins


def get_middleware_health() -> Dict[str, Any]:
    """Get middleware health status"""

    return {
        "middleware_status": "healthy",
        "components": {
            "cors": "configured",
            "rate_limiting": "active",
            "request_logging": "optional"
        },
        "timestamp": datetime.utcnow().isoformat()
    }
