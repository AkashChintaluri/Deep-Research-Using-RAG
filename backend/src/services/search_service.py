"""
Search service for handling search operations.
"""

import logging
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor

from ..models.search import SearchResult, DatabaseStats
from ..core.config import Config
from .faiss_service import FAISSService
from .postgres_service import PostgresService

logger = logging.getLogger(__name__)

class SearchService:
    """Service for handling search operations."""
    
    def __init__(self):
        self.faiss_service = FAISSService()
        self.postgres_service = PostgresService()
    
    async def search_papers(self, query: str, n_results: int = 5, search_type: str = "faiss") -> List[SearchResult]:
        """Search papers using FAISS for vector retrieval and PostgreSQL for full details."""
        try:
            results = []
            
            if search_type in ["postgres", "both"]:
                postgres_results = await self.postgres_service.search(query, n_results)
                results.extend(postgres_results)
            
            if search_type in ["faiss", "both"]:
                # Use FAISS for vector retrieval
                faiss_results = await self.faiss_service.search(query, n_results)
                
                # Get full paper details from PostgreSQL for each FAISS result
                enhanced_results = []
                for result in faiss_results:
                    if result.paper_id:
                        # Get full paper details from PostgreSQL
                        paper_details = await self._get_paper_details(result.paper_id)
                        if paper_details:
                            # Update result with full details from PostgreSQL
                            result.title = paper_details.get('title', result.title)
                            result.authors = paper_details.get('authors', result.authors)
                            result.abstract = paper_details.get('abstract', result.abstract)
                            result.categories = paper_details.get('categories')
                            result.text_length = paper_details.get('text_length')
                            result.word_count = paper_details.get('word_count')
                            result.pdf_path = paper_details.get('pdf_path')
                            
                            # Add full text preview from PostgreSQL
                            full_text = paper_details.get('full_text', '')
                            if full_text:
                                result.full_text_preview = full_text[:300] + "..." if len(full_text) > 300 else full_text
                        
                        enhanced_results.append(result)
                
                results.extend(enhanced_results)
            
            # Sort by score and limit results
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:n_results]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    async def get_database_stats(self) -> DatabaseStats:
        """Get database statistics."""
        try:
            return await self.postgres_service.get_stats()
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            raise
    
    async def _get_paper_details(self, paper_id: str) -> Dict[str, Any]:
        """Get full paper details from PostgreSQL."""
        try:
            with self.postgres_service.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, title, authors, abstract, categories, full_text, 
                           text_length, word_count, pdf_path
                    FROM papers 
                    WHERE id = %s
                """, (paper_id,))
                paper = cursor.fetchone()
                
                if paper:
                    paper_dict = dict(paper)
                    
                    # Fix authors if they are incorrect (subtitle instead of actual authors)
                    if paper_dict.get('authors') and paper_dict.get('full_text'):
                        authors = paper_dict['authors']
                        full_text = paper_dict['full_text']
                        
                        # Check if authors field contains subtitle instead of actual authors
                        if (authors in full_text[:200] or 
                            authors == "Unknown Authors" or 
                            len(authors) > 100):  # Likely a subtitle if too long
                            
                            # Try to extract real authors from full text
                            real_authors = self._extract_authors_from_text(full_text)
                            if real_authors:
                                paper_dict['authors'] = real_authors
                                logger.info(f"Fixed authors for {paper_id}: {real_authors[:50]}...")
                    
                    return paper_dict
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get paper details for {paper_id}: {e}")
            return {}
    
    def _extract_authors_from_text(self, full_text: str) -> str:
        """Extract real authors from full text."""
        try:
            # Look for common author patterns in the first 1000 characters
            text_start = full_text[:1000]
            
            # Pattern 1: Look for numbered author lists (1 2 3 4 5 Author Name)
            import re
            
            # Find patterns like "1 2 3 4 5 Paul Harvey , Bruno Merın , Tracy L. Huard"
            author_pattern = r'(?:\d+\s+)+([A-Z][a-zA-Z\s\.]+(?:,\s*[A-Z][a-zA-Z\s\.]+)*)'
            matches = re.findall(author_pattern, text_start)
            
            if matches:
                # Take the first match and clean it up
                authors = matches[0].strip()
                # Remove extra spaces and clean up
                authors = re.sub(r'\s+', ' ', authors)
                return authors
            
            # Pattern 2: Look for "ABSTRACT" and take text before it
            abstract_pos = text_start.find('ABSTRACT')
            if abstract_pos > 0:
                before_abstract = text_start[:abstract_pos]
                # Look for author names (capitalized words)
                author_names = re.findall(r'[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', before_abstract)
                if author_names:
                    return ', '.join(author_names[:10])  # Limit to first 10 authors
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract authors from text: {e}")
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Check FAISS
            faiss_health = await self.faiss_service.health_check()
            
            # Check PostgreSQL
            postgres_health = await self.postgres_service.health_check()
            
            return {
                "status": "healthy",
                "faiss": faiss_health,
                "postgresql": postgres_health
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise
