#!/usr/bin/env python3
"""
Update Pinecone vectors with correct metadata from the updated database.
This script updates the metadata in Pinecone vectors without regenerating embeddings.
"""

import sys
import logging
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# Add src to path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_dir))

from services.pinecone_integration import PineconeManager, PineconeConfig
from core.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_pinecone_metadata():
    """Update Pinecone vectors with correct metadata from database."""
    try:
        # Connect to database
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='Codemate',
            user='postgres',
            password='akash'
        )
        
        # Get all papers with correct metadata
        logger.info("Loading correct metadata from database...")
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, title, authors, abstract, categories
                FROM papers
                ORDER BY id
            """)
            papers = cursor.fetchall()
        
        logger.info(f"Found {len(papers)} papers with correct metadata")
        
        # Connect to Pinecone
        pinecone_config = PineconeConfig(
            api_key=Config.PINECONE_API_KEY,
            index_name=Config.PINECONE_INDEX_NAME,
            environment=Config.PINECONE_ENVIRONMENT
        )
        
        manager = PineconeManager(pinecone_config)
        logger.info("Connected to Pinecone")
        
        # Create a mapping of paper_id to correct metadata
        paper_metadata = {paper['id']: dict(paper) for paper in papers}
        
        # Get all vectors from Pinecone and update their metadata
        logger.info("Fetching vectors from Pinecone...")
        
        # Get index stats
        stats = manager.index.describe_index_stats()
        total_vectors = stats.total_vector_count
        logger.info(f"Total vectors in Pinecone: {total_vectors}")
        
        # Process in batches
        batch_size = 100
        updated_count = 0
        not_found_count = 0
        
        # Query all vectors (this might be expensive for large indexes)
        # For now, let's try to get a sample and update those
        logger.info("Note: This will update vectors in batches. Large indexes may take time.")
        
        # Get vectors by querying with a dummy vector
        dummy_vector = [0.0] * 384  # 384 is the embedding dimension
        
        # Get all vectors by querying with a very low similarity threshold
        # This is a workaround since Pinecone doesn't have a direct "get all" method
        logger.info("Fetching vectors from Pinecone (this may take a while)...")
        
        # We'll need to query multiple times to get all vectors
        # For now, let's update based on the paper IDs we know exist
        for paper_id, metadata in paper_metadata.items():
            try:
                # Query Pinecone for vectors with this doc_id
                results = manager.index.query(
                    vector=dummy_vector,
                    top_k=1000,  # Get up to 1000 vectors
                    include_metadata=True,
                    filter={"doc_id": paper_id}
                )
                
                if results.matches:
                    # Update each vector with correct metadata
                    vectors_to_update = []
                    for match in results.matches:
                        # Create updated vector with correct metadata
                        updated_vector = {
                            "id": match.id,
                            "values": match.values,  # Keep existing embedding
                            "metadata": {
                                **match.metadata,  # Keep existing metadata
                                "title": metadata['title'],
                                "authors": metadata['authors'],
                                "abstract": metadata['abstract'][:1000] if metadata['abstract'] else "",
                                "categories": metadata['categories'] or ""
                            }
                        }
                        vectors_to_update.append(updated_vector)
                    
                    # Update vectors in Pinecone
                    if vectors_to_update:
                        manager.index.upsert(vectors=vectors_to_update)
                        updated_count += len(vectors_to_update)
                        logger.info(f"Updated {len(vectors_to_update)} vectors for paper {paper_id}")
                else:
                    not_found_count += 1
                    if not_found_count % 50 == 0:
                        logger.info(f"Not found in Pinecone: {not_found_count} papers...")
                
            except Exception as e:
                logger.error(f"Error updating vectors for paper {paper_id}: {e}")
                continue
        
        logger.info(f"Update completed!")
        logger.info(f"Updated vectors: {updated_count}")
        logger.info(f"Papers not found in Pinecone: {not_found_count}")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to update Pinecone metadata: {e}")
        raise

if __name__ == "__main__":
    update_pinecone_metadata()
