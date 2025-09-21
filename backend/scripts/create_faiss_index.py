#!/usr/bin/env python3
"""
Create FAISS index from existing chunks.
"""

import sys
import logging
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_dir))

from services.faiss_service import FAISSService

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
        
        # Initialize FAISS service
        faiss_service = FAISSService()
        
        # Path to chunks file
        chunks_file = Path(__file__).parent.parent / 'data' / 'processed' / 'arxiv_chunks.jsonl'
        
        if not chunks_file.exists():
            logger.error(f"Chunks file not found: {chunks_file}")
            return
        
        # Create index from chunks
        faiss_service.create_index_from_chunks(str(chunks_file))
        
        logger.info("[OK] FAISS index created successfully!")
        
    except Exception as e:
        logger.error(f"Failed to create FAISS index: {e}")
        raise

if __name__ == "__main__":
    main()
