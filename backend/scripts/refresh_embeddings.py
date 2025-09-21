#!/usr/bin/env python3
"""
Refresh embeddings and upload to Pinecone with correct metadata.
This script skips PDF processing and works with existing chunks.
"""

import sys
import logging
from pathlib import Path
import os

# Add src to path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_dir))

# Change to backend directory
os.chdir(Path(__file__).parent.parent)

from src.services.embedding_generation import EmbeddingPipeline, EmbeddingConfig
from src.services.pinecone_integration import PineconePipeline, PineconeConfig
from src.services.faiss_indexing import FAISSPipeline, FAISSConfig
from src.core.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clear_pinecone_index():
    """Clear all vectors from Pinecone index."""
    try:
        logger.info("Clearing Pinecone index...")
        
        pinecone_config = PineconeConfig(
            api_key=Config.PINECONE_API_KEY,
            index_name=Config.PINECONE_INDEX_NAME,
            environment=Config.PINECONE_ENVIRONMENT
        )
        
        pinecone_pipeline = PineconePipeline(pinecone_config)
        pinecone_pipeline.manager.connect()
        
        # Delete all vectors by querying with a dummy vector and deleting all results
        # This is a workaround since Pinecone doesn't have a direct "delete all" method
        dummy_vector = [0.0] * 384
        
        # Get all vectors and delete them
        stats = pinecone_pipeline.manager.index.describe_index_stats()
        total_vectors = stats.total_vector_count
        
        if total_vectors > 0:
            logger.info(f"Found {total_vectors} vectors to delete...")
            
            # Query all vectors (this might take a while for large indexes)
            results = pinecone_pipeline.manager.index.query(
                vector=dummy_vector,
                top_k=10000,  # Get up to 10k vectors at a time
                include_metadata=True
            )
            
            if results.matches:
                # Delete vectors in batches
                vector_ids = [match.id for match in results.matches]
                pinecone_pipeline.manager.index.delete(ids=vector_ids)
                logger.info(f"Deleted {len(vector_ids)} vectors")
            
            # Repeat until all vectors are deleted
            while True:
                stats = pinecone_pipeline.manager.index.describe_index_stats()
                if stats.total_vector_count == 0:
                    break
                
                results = pinecone_pipeline.manager.index.query(
                    vector=dummy_vector,
                    top_k=10000,
                    include_metadata=True
                )
                
                if not results.matches:
                    break
                
                vector_ids = [match.id for match in results.matches]
                pinecone_pipeline.manager.index.delete(ids=vector_ids)
                logger.info(f"Deleted {len(vector_ids)} more vectors")
        
        logger.info("✅ Pinecone index cleared successfully!")
        
    except Exception as e:
        logger.error(f"Failed to clear Pinecone index: {e}")
        raise

def refresh_embeddings_and_upload():
    """Refresh embeddings with correct metadata and upload to Pinecone."""
    try:
        logger.info("Starting embedding refresh and upload...")
        
        # Step 1: Clear Pinecone
        clear_pinecone_index()
        
        # Step 2: Create embedding configuration
        embedding_config = EmbeddingConfig(
            model_name='sentence-transformers/all-MiniLM-L6-v2',
            batch_size=32,
            vector_dimension=384,
            normalize_vectors=True,
            use_pinecone=True,
            pinecone_api_key=Config.PINECONE_API_KEY,
            pinecone_index_name=Config.PINECONE_INDEX_NAME,
            pinecone_environment=Config.PINECONE_ENVIRONMENT,
            use_faiss=True,
            faiss_index_type='IndexFlatIP',
            faiss_metadata_file=str(Path(Config.PROCESSED_DATA_DIR) / 'faiss_metadata.jsonl'),
            faiss_index_file=str(Path(Config.PROCESSED_DATA_DIR) / 'faiss_index.bin')
        )
        
        # Step 3: Create embedding pipeline
        pipeline = EmbeddingPipeline(embedding_config)
        
        # Step 4: Process existing chunks with Pinecone upload
        chunks_file = Path(Config.PROCESSED_DATA_DIR) / 'arxiv_chunks.jsonl'
        embeddings_file = Path(Config.PROCESSED_DATA_DIR) / 'arxiv_embeddings.jsonl'
        
        if not chunks_file.exists():
            logger.error(f"Chunks file not found: {chunks_file}")
            return
        
        logger.info("Processing chunks and generating embeddings...")
        pipeline.process_chunks_file_with_pinecone(
            str(chunks_file), 
            str(embeddings_file), 
            batch_size=1000
        )
        
        logger.info("✅ Embedding refresh and upload completed!")
        logger.info(f"Processed chunks: {pipeline.processed_chunks}")
        logger.info(f"Total embeddings: {pipeline.total_embeddings}")
        
    except Exception as e:
        logger.error(f"Failed to refresh embeddings: {e}")
        raise

def main():
    """Main function."""
    try:
        logger.info("🔄 Refreshing embeddings and uploading to Pinecone...")
        logger.info("=" * 60)
        
        refresh_embeddings_and_upload()
        
        logger.info("🎉 All done! Embeddings refreshed and uploaded to Pinecone.")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise

if __name__ == "__main__":
    main()
