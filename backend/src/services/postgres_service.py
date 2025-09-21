"""
PostgreSQL service for database operations.
"""

import logging
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor

from ..models.search import SearchResult, DatabaseStats
from ..core.config import Config

logger = logging.getLogger(__name__)

class PostgresService:
    """Service for PostgreSQL operations."""
    
    def __init__(self):
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Connect to PostgreSQL database."""
        try:
            self.connection = psycopg2.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD
            )
            logger.info("[OK] PostgreSQL connected successfully!")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    async def search(self, query: str, n_results: int) -> List[SearchResult]:
        """Search using PostgreSQL full-text search."""
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                search_query = """
                    SELECT id, title, authors, abstract, categories, full_text, text_length, word_count, pdf_path,
                           ts_rank(to_tsvector('english', title || ' ' || abstract || ' ' || COALESCE(full_text, '')),
                                   plainto_tsquery('english', %s)) as rank
                    FROM papers
                    WHERE to_tsvector('english', title || ' ' || abstract || ' ' || COALESCE(full_text, ''))
                          @@ plainto_tsquery('english', %s)
                    ORDER BY rank DESC
                    LIMIT %s
                """
                cursor.execute(search_query, (query, query, n_results))
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    # Create full text preview (first 300 chars)
                    full_text_preview = None
                    if row['full_text']:
                        full_text_preview = row['full_text'][:300] + "..." if len(row['full_text']) > 300 else row['full_text']
                    
                    results.append(SearchResult(
                        paper_id=row['id'],
                        title=row['title'],
                        authors=row['authors'],
                        abstract=row['abstract'][:500] + "..." if len(row['abstract']) > 500 else row['abstract'],
                        score=float(row['rank']),
                        search_type="postgres",
                        categories=row.get('categories'),
                        text_length=row.get('text_length'),
                        word_count=row.get('word_count'),
                        pdf_path=row.get('pdf_path'),
                        full_text_preview=full_text_preview
                    ))
                
                return results
                
        except Exception as e:
            logger.error(f"PostgreSQL search failed: {e}")
            return []
    
    async def get_stats(self) -> DatabaseStats:
        """Get database statistics."""
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get total papers
                cursor.execute("SELECT COUNT(*) as total FROM papers")
                total_papers = cursor.fetchone()['total']
                
                # Get papers with full text
                cursor.execute("SELECT COUNT(*) as count FROM papers WHERE full_text IS NOT NULL AND LENGTH(full_text) > 0")
                papers_with_full_text = cursor.fetchone()['count']
                
                # Get average text length
                cursor.execute("SELECT AVG(LENGTH(full_text)) as avg_length FROM papers WHERE full_text IS NOT NULL")
                avg_length = cursor.fetchone()['avg_length'] or 0
                
                # Get top categories
                cursor.execute("""
                    SELECT categories, COUNT(*) as count 
                    FROM papers 
                    GROUP BY categories 
                    ORDER BY count DESC 
                    LIMIT 5
                """)
                top_categories = [{"category": row['categories'], "count": row['count']} for row in cursor.fetchall()]
            
            return DatabaseStats(
                total_papers=total_papers,
                papers_with_full_text=papers_with_full_text,
                average_text_length=int(avg_length),
                top_categories=top_categories
            )
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check PostgreSQL health."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM papers")
                paper_count = cursor.fetchone()[0]
            
            return {
                "connected": True,
                "total_papers": paper_count
            }
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return {
                "connected": False,
                "error": str(e)
            }
