"""
API endpoints for the RAG system.
"""

from src.api.search import router as search_router
from src.api.health import router as health_router
from src.api.chat import router as chat_router

__all__ = ["search_router", "health_router", "chat_router"]
