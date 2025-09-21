#!/usr/bin/env python3
"""
Pinecone Integration Module for ArXiv Data Processing
====================================================

This module handles storing and searching embeddings using Pinecone vector database.
It provides high-performance vector similarity search with metadata filtering.

Key Features:
- Store embeddings in Pinecone indexes
- Vector similarity search with cosine similarity
- Metadata filtering and querying
- Batch operations for efficiency
- Index management
- Support for multiple vector dimensions
"""

import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import tqdm
import os
import sys
import uuid

from ..core.config import Config

try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    print("Warning: Pinecone not installed. Install with: pip install pinecone")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pinecone_integration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class PineconeConfig:
    """Configuration for Pinecone integration."""
    api_key: str = None
    environment: str = None
    index_name: str = None
    dimension: int = 384
    metric: str = "cosine"  # cosine, euclidean, dotproduct
    pods: int = 1
    replicas: int = 1
    pod_type: str = "p1.x1"  # p1.x1, p1.x2, p1.x4, p1.x8
    # Serverless configuration
    cloud: str = "aws"  # aws, gcp, azure
    region: str = "us-east-1"
    
    def __post_init__(self):
        """Initialize with default values from Config if not provided."""
        if self.api_key is None:
            self.api_key = Config.PINECONE_API_KEY
        if self.environment is None:
            self.environment = Config.PINECONE_ENVIRONMENT
        if self.index_name is None:
            self.index_name = Config.PINECONE_INDEX_NAME
        if self.dimension is None:
            self.dimension = Config.PINECONE_DIMENSION


class PineconeManager:
    """Manages Pinecone operations for ArXiv data."""
    
    def __init__(self, config: PineconeConfig = None):
        """
        Initialize the Pinecone manager.
        
        Args:
            config: Pinecone configuration
        """
        if not PINECONE_AVAILABLE:
            raise ImportError("Pinecone not available. Install with: pip install pinecone")
        
        self.config = config or PineconeConfig()
        self.pc = None
        self.index = None
        
    def connect(self):
        """Connect to Pinecone and initialize index."""
        try:
            logger.info(f"Connecting to Pinecone...")
            
            # Initialize Pinecone client
            self.pc = Pinecone(api_key=self.config.api_key)
            
            # Check if index exists
            existing_indexes = self.pc.list_indexes()
            index_names = [idx.name for idx in existing_indexes]
            
            if self.config.index_name in index_names:
                logger.info(f"Using existing index: {self.config.index_name}")
                self.index = self.pc.Index(self.config.index_name)
            else:
                logger.info(f"Creating new index: {self.config.index_name}")
                self._create_index()
                self.index = self.pc.Index(self.config.index_name)
            
            # Get index stats
            stats = self.index.describe_index_stats()
            logger.info(f"Index stats: {stats}")
            logger.info("[OK] Successfully connected to Pinecone!")
            
        except Exception as e:
            logger.error(f"Failed to connect to Pinecone: {e}")
            raise
    
    def _create_index(self):
        """Create a new Pinecone index."""
        try:
            # Create index with serverless configuration
            self.pc.create_index(
                name=self.config.index_name,
                dimension=self.config.dimension,
                metric=self.config.metric,
                spec=ServerlessSpec(
                    cloud=self.config.cloud,
                    region=self.config.region
                )
            )
            logger.info(f"Created index: {self.config.index_name}")
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            raise
    
    def upsert_vectors(self, vectors: List[Dict[str, Any]], batch_size: int = 100):
        """
        Upsert vectors to Pinecone index.
        
        Args:
            vectors: List of vectors with id, values, and metadata
            batch_size: Number of vectors per batch
        """
        if not self.index:
            raise ValueError("Not connected to Pinecone. Call connect() first.")
        
        logger.info(f"Upserting {len(vectors)} vectors to Pinecone")
        
        # Process vectors in batches
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            
            try:
                # Upsert batch
                self.index.upsert(vectors=batch)
                logger.info(f"Upserted batch {i//batch_size + 1} ({len(batch)} vectors)")
                
            except Exception as e:
                logger.error(f"Error upserting batch {i//batch_size + 1}: {e}")
                continue
    
    def search(self, query_vector: np.ndarray, top_k: int = 10, 
              filter_dict: Dict[str, Any] = None, include_metadata: bool = True) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query vector
            top_k: Number of results to return
            filter_dict: Optional metadata filters
            include_metadata: Whether to include metadata in results
            
        Returns:
            List of search results
        """
        if not self.index:
            raise ValueError("Not connected to Pinecone. Call connect() first.")
        
        try:
            # Convert query vector to list
            query_vector_list = query_vector.tolist()
            
            # Search
            results = self.index.query(
                vector=query_vector_list,
                top_k=top_k,
                filter=filter_dict,
                include_metadata=include_metadata
            )
            
            # Format results
            formatted_results = []
            for match in results.matches:
                result = {
                    'id': match.id,
                    'score': match.score,
                    'metadata': match.metadata or {}
                }
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching Pinecone: {e}")
            return []
    
    def delete_vectors(self, vector_ids: List[str]):
        """
        Delete vectors by IDs.
        
        Args:
            vector_ids: List of vector IDs to delete
        """
        if not self.index:
            raise ValueError("Not connected to Pinecone. Call connect() first.")
        
        try:
            self.index.delete(ids=vector_ids)
            logger.info(f"Deleted {len(vector_ids)} vectors")
        except Exception as e:
            logger.error(f"Error deleting vectors: {e}")
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        if not self.index:
            return {"status": "Not connected"}
        
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": stats.namespaces
            }
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {"status": f"Error: {e}"}


class PineconePipeline:
    """Pipeline for storing and searching documents in Pinecone."""
    
    def __init__(self, config: PineconeConfig = None):
        """
        Initialize the Pinecone pipeline.
        
        Args:
            config: Pinecone configuration
        """
        self.config = config or PineconeConfig()
        self.manager = PineconeManager(config)
        self.processed_documents = 0
    
    def process_chunks_file(self, chunks_file: str, batch_size: int = 100):
        """
        Process chunks from a JSONL file and store in Pinecone.
        
        Args:
            chunks_file: Path to input JSONL file with chunks
            batch_size: Number of vectors to process in each batch
        """
        logger.info(f"Starting Pinecone processing for {chunks_file}")
        
        chunks_path = Path(chunks_file)
        if not chunks_path.exists():
            raise FileNotFoundError(f"Chunks file {chunks_file} not found")
        
        # Connect to Pinecone
        self.manager.connect()
        
        # Process chunks and prepare vectors
        vectors = []
        
        with open(chunks_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(tqdm.tqdm(f, desc="Processing chunks")):
                if not line.strip():
                    continue
                
                try:
                    chunk = json.loads(line.strip())
                    
                    # Check if chunk has embedding
                    if 'embedding' not in chunk:
                        logger.warning(f"Chunk {line_num + 1} has no embedding, skipping")
                        continue
                    
                    # Create vector for Pinecone
                    vector = {
                        "id": chunk.get('chunk_id', f"chunk_{line_num}"),
                        "values": chunk['embedding'],
                        "metadata": {
                            "doc_id": chunk.get('doc_id'),
                            "chunk_index": chunk.get('chunk_index'),
                            "title": chunk.get('title'),
                            "authors": chunk.get('authors'),
                            "version": chunk.get('version'),
                            "text": chunk.get('text', '')[:1000],  # Truncate for metadata
                            "token_count": chunk.get('token_count'),
                            "char_count": chunk.get('char_count'),
                            "line_number": line_num + 1,
                            "processed_at": datetime.utcnow().isoformat()
                        }
                    }
                    
                    vectors.append(vector)
                    self.processed_documents += 1
                    
                    # Process batch when it reaches batch_size
                    if len(vectors) >= batch_size:
                        self.manager.upsert_vectors(vectors, batch_size)
                        vectors = []
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Error parsing line {line_num + 1}: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing chunk at line {line_num + 1}: {e}")
                    continue
        
        # Process remaining vectors
        if vectors:
            self.manager.upsert_vectors(vectors, batch_size)
        
        logger.info(f"Pinecone processing completed!")
        logger.info(f"Processed documents: {self.processed_documents}")
        logger.info(f"Index stats: {self.manager.get_index_stats()}")
    
    def search(self, query_vector: np.ndarray, top_k: int = 10, 
              filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            query_vector: Query vector
            top_k: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of similar documents
        """
        return self.manager.search(query_vector, top_k, filters)


def main():
    """Main function for testing Pinecone integration."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Pinecone integration')
    parser.add_argument('--chunks-file', help='Input chunks JSONL file')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing')
    parser.add_argument('--info', action='store_true', help='Show index information')
    
    args = parser.parse_args()
    
    # Create configuration
    config = PineconeConfig()
    
    # Create pipeline
    pipeline = PineconePipeline(config)
    
    if args.info:
        # Show index information
        pipeline.manager.connect()
        stats = pipeline.manager.get_index_stats()
        print("=" * 50)
        print("Pinecone Index Information")
        print("=" * 50)
        for key, value in stats.items():
            print(f"{key}: {value}")
        print("=" * 50)
        
    elif args.chunks_file:
        # Process chunks file
        pipeline.process_chunks_file(args.chunks_file, args.batch_size)
        print("[OK] Pinecone processing completed!")
    
    else:
        print("[ERROR] You must specify --chunks-file or --info")
        parser.print_help()


if __name__ == "__main__":
    main()
