#!/usr/bin/env python3
"""
Create FAISS index from existing chunks - simple version.
"""

import sys
import logging
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_dir))

from services.faiss_indexing import FAISSPipeline, FAISSConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Create FAISS index from chunks."""
    try:
        logger.info("Creating FAISS index from chunks...")
        
        # Path to chunks file
        chunks_file = Path(__file__).parent.parent / 'data' / 'processed' / 'arxiv_chunks.jsonl'
        
        if not chunks_file.exists():
            logger.error(f"Chunks file not found: {chunks_file}")
            return
        
        # Create FAISS configuration
        config = FAISSConfig(
            index_type='IndexFlatIP',
            vector_dimension=384,
            normalize_vectors=True
        )
        
        # Create pipeline and process chunks
        pipeline = FAISSPipeline(config)
        pipeline.process_chunks_file(str(chunks_file))
        
        logger.info("[OK] FAISS index created successfully!")
        
    except Exception as e:
        logger.error(f"Failed to create FAISS index: {e}")
        raise

if __name__ == "__main__":
    main()
