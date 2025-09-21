"""
Health check API endpoints.
"""

from fastapi import APIRouter, HTTPException
import logging

from src.services.search_service import SearchService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["health"])

# Initialize search service
search_service = SearchService()

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        health_status = await search_service.health_check()
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")
