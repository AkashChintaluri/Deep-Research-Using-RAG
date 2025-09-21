"""
FAISS service for local vector search operations.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Tuple
from pathlib import Path

from ..models.search import SearchResult
from ..core.config import Config
from .embedding_service import EmbeddingService
from .faiss_indexing import FAISSPipeline, FAISSConfig

logger = logging.getLogger(__name__)

class FAISSService:
    """Service for FAISS vector operations with caching."""
    
    _instance = None
    _pipeline = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super(FAISSService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.embedding_service = EmbeddingService()
            self.pipeline = None
            self._initialize_pipeline()
            self.initialized = True
    
    def _initialize_pipeline(self):
        """Initialize FAISS pipeline with caching."""
        try:
            # Use cached pipeline if available
            if FAISSService._pipeline is not None:
                self.pipeline = FAISSService._pipeline
                logger.info("[OK] FAISS service initialized with cached pipeline!")
                return
            
            # Create FAISS configuration
            config = FAISSConfig(
                index_type='IndexFlatIP',
                vector_dimension=384,  # Sentence transformer dimension
                metadata_file=Path(Config.PROCESSED_DATA_DIR) / 'faiss_metadata.jsonl',
                index_file=Path(Config.PROCESSED_DATA_DIR) / 'faiss_index.bin',
                normalize_vectors=True
            )
            
            self.pipeline = FAISSPipeline(config)
            
            # Try to load existing index
            try:
                # Convert Path objects to strings for FAISS
                index_path = str(config.index_file)
                metadata_path = str(config.metadata_file)
                self.pipeline.indexer.load_index(index_path, metadata_path)
                # Cache the pipeline for future use
                FAISSService._pipeline = self.pipeline
                logger.info("[OK] FAISS index loaded successfully and cached!")
            except FileNotFoundError:
                logger.warning("FAISS index not found. Will need to create index first.")
                self.pipeline = None
            except Exception as e:
                logger.error(f"Failed to load FAISS index: {e}")
                self.pipeline = None
                
        except Exception as e:
            logger.error(f"Failed to initialize FAISS pipeline: {e}")
            self.pipeline = None
    
    async def search(self, query: str, n_results: int) -> List[SearchResult]:
        """Search using FAISS vector search."""
        try:
            if self.pipeline is None:
                logger.error("FAISS pipeline not initialized")
                return []
            
            # Generate query embedding
            query_embedding = self.embedding_service.generate_embedding(query)
            
            # Search FAISS index
            distances, metadata_list = self.pipeline.search(query_embedding, n_results)
            
            results = []
            for i, (distance, metadata) in enumerate(zip(distances, metadata_list)):
                if metadata:
                    # Create SearchResult with metadata from FAISS
                    results.append(SearchResult(
                        paper_id=metadata.get('doc_id'),
                        title=metadata.get('title', ''),
                        authors=metadata.get('authors', ''),
                        abstract=metadata.get('text', '')[:500] + "..." if len(metadata.get('text', '')) > 500 else metadata.get('text', ''),
                        score=float(distance),
                        search_type="faiss",
                        chunk_id=metadata.get('chunk_id'),
                        text=metadata.get('text', '')[:200] + "..." if len(metadata.get('text', '')) > 200 else metadata.get('text', '')
                    ))
            
            return results
            
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Check FAISS health."""
        try:
            if self.pipeline is None:
                return {
                    "connected": False,
                    "error": "FAISS pipeline not initialized"
                }
            
            if self.pipeline.indexer.index is None:
                return {
                    "connected": False,
                    "error": "FAISS index not loaded"
                }
            
            index_info = self.pipeline.indexer.get_index_info()
            return {
                "connected": True,
                "total_vectors": index_info.get("total_vectors", 0),
                "vector_dimension": index_info.get("vector_dimension", 0),
                "index_type": index_info.get("index_type", "unknown")
            }
        except Exception as e:
            logger.error(f"FAISS health check failed: {e}")
            return {
                "connected": False,
                "error": str(e)
            }
    
    def create_index_from_chunks(self, chunks_file: str):
        """Create FAISS index from chunks file."""
        try:
            if self.pipeline is None:
                self._initialize_pipeline()
            
            if self.pipeline is None:
                raise Exception("Failed to initialize FAISS pipeline")
            
            # Process chunks file to create index
            self.pipeline.process_chunks_file(chunks_file)
            logger.info("[OK] FAISS index created successfully!")
            
        except Exception as e:
            logger.error(f"Failed to create FAISS index: {e}")
            raise
