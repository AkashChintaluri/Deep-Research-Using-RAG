"""
Search API endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List
import logging

from src.models.search import SearchRequest, SearchResult, DatabaseStats
from src.services.search_service import SearchService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["search"])

# Initialize search service
search_service = SearchService()

@router.post("/search", response_model=List[SearchResult])
async def search_papers(request: SearchRequest):
    """Search papers using PostgreSQL, Pinecone, or both."""
    try:
        results = await search_service.search_papers(
            query=request.query,
            n_results=request.n_results,
            search_type=request.search_type
        )
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

@router.get("/search", response_model=List[SearchResult])
async def search_papers_get(
    query: str = Query(..., description="Search query"),
    n_results: int = Query(5, description="Number of results to return"),
    search_type: str = Query("faiss", description="Search type: postgres, faiss, pinecone, or both")
):
    """Search papers using GET method."""
    try:
        results = await search_service.search_papers(
            query=query,
            n_results=n_results,
            search_type=search_type
        )
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

@router.get("/stats", response_model=DatabaseStats)
async def get_database_stats():
    """Get database statistics."""
    try:
        stats = await search_service.get_database_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get database stats: {e}")
