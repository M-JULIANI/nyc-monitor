"""API endpoints for the RAG backend."""

from .chat_endpoints import chat_router
from .investigation_endpoints import investigation_router
from .auth_endpoints import auth_router
from .admin_endpoints import admin_router

__all__ = ["chat_router", "investigation_router",
           "auth_router", "admin_router"]
