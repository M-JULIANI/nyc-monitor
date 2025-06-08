"""API endpoints for the RAG backend."""

from .chat_endpoints import chat_router
from .investigation_endpoints import investigation_router

__all__ = ["chat_router", "investigation_router"]
