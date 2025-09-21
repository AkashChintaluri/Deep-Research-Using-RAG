"""
Pinecone service for vector operations.
"""

import logging
from typing import List, Dict, Any
import numpy as np

from ..models.search import SearchResult
from ..core.config import Config
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class PineconeService:
    """Service for Pinecone vector operations."""
    
    def __init__(self):
        self.pipeline = None
        self.embedding_service = EmbeddingService()
        self._connect()
    
    def _connect(self):
        """Connect to Pinecone."""
        try:
            from .pinecone_integration import PineconePipeline, PineconeConfig
            
            config = PineconeConfig(
                api_key=Config.PINECONE_API_KEY,
                index_name=Config.PINECONE_INDEX_NAME,
                environment=Config.PINECONE_ENVIRONMENT
            )
            self.pipeline = PineconePipeline(config)
            self.pipeline.manager.connect()
            logger.info("[OK] Pinecone connected successfully!")
        except Exception as e:
            logger.error(f"Failed to connect to Pinecone: {e}")
            raise
    
    async def search(self, query: str, n_results: int) -> List[SearchResult]:
        """Search using Pinecone vector search."""
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.generate_embedding(query)
            
            # Search Pinecone
            search_results = self.pipeline.manager.index.query(
                vector=query_embedding.tolist(),
                top_k=n_results,
                include_metadata=True
            )
            
            results = []
            for match in search_results.matches:
                # Get full paper details from database
                from .postgres_service import PostgresService
                from psycopg2.extras import RealDictCursor
                postgres_service = PostgresService()
                
                with postgres_service.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, title, authors, abstract 
                        FROM papers 
                        WHERE id = %s
                    """, (match.metadata.get('doc_id'),))
                    paper = cursor.fetchone()
                    
                    if paper:
                        results.append(SearchResult(
                            paper_id=paper['id'],
                            title=paper['title'],
                            authors=paper['authors'],
                            abstract=paper['abstract'][:500] + "..." if len(paper['abstract']) > 500 else paper['abstract'],
                            score=float(match.score),
                            search_type="pinecone",
                            chunk_id=match.metadata.get('chunk_id'),
                            text=match.metadata.get('text', '')[:200] + "..." if match.metadata.get('text') else None
                        ))
            
            return results
            
        except Exception as e:
            logger.error(f"Pinecone search failed: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Pinecone health."""
        try:
            stats = self.pipeline.manager.index.describe_index_stats()
            return {
                "connected": True,
                "total_vectors": stats.total_vector_count
            }
        except Exception as e:
            logger.error(f"Pinecone health check failed: {e}")
            return {
                "connected": False,
                "error": str(e)
            }
