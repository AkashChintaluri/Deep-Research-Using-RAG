#!/usr/bin/env python3
"""
FAISS Vector Indexing Module for ArXiv Data Processing
=====================================================

This module handles creating and managing FAISS vector indexes for document chunks.
It provides efficient similarity search and stores metadata separately for provenance.

Key Features:
- FAISS IndexFlatIP for inner product similarity
- HNSW index for larger datasets
- Metadata storage in JSONL format
- Batch indexing for efficiency
- Index persistence and loading
- Similarity search with metadata retrieval
"""

import json
import logging
import numpy as np
from pathlib import Path

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("Warning: FAISS not installed. Install with: pip install faiss-cpu")
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import tqdm
import os
import sys

from ..core.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('faiss_indexing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class FAISSConfig:
    """Configuration for FAISS indexing."""
    index_type: str = 'IndexFlatIP'  # IndexFlatIP, HNSW
    vector_dimension: int = 384
    metadata_file: str = None
    index_file: str = None
    normalize_vectors: bool = True
    # HNSW parameters
    hnsw_m: int = 16
    hnsw_ef_construction: int = 200
    hnsw_ef_search: int = 50


class FAISSIndexer:
    """Handles FAISS vector indexing operations."""
    
    def __init__(self, config: FAISSConfig = None):
        """
        Initialize the FAISS indexer.
        
        Args:
            config: FAISS configuration
        """
        self.config = config or FAISSConfig()
        self.index = None
        self.metadata = []
        self.vector_dimension = self.config.vector_dimension
        
        # Set default file paths if not provided
        if self.config.metadata_file is None:
            self.config.metadata_file = os.path.join(
                Config.PROCESSED_DATA_DIR, 'faiss_metadata.jsonl'
            )
        if self.config.index_file is None:
            self.config.index_file = os.path.join(
                Config.PROCESSED_DATA_DIR, 'faiss_index.bin'
            )
    
    def create_index(self, vector_dimension: int = None):
        """
        Create a new FAISS index.
        
        Args:
            vector_dimension: Dimension of the vectors
        """
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS not available. Install with: pip install faiss-cpu")
        
        if vector_dimension:
            self.vector_dimension = vector_dimension
            self.config.vector_dimension = vector_dimension
        
        logger.info(f"Creating FAISS {self.config.index_type} index with dimension {self.vector_dimension}")
        
        if self.config.index_type == 'IndexFlatIP':
            # Inner product index (for normalized vectors, equivalent to cosine similarity)
            self.index = faiss.IndexFlatIP(self.vector_dimension)
        elif self.config.index_type == 'HNSW':
            # Hierarchical Navigable Small World index for larger datasets
            self.index = faiss.IndexHNSWFlat(self.vector_dimension, self.config.hnsw_m)
            self.index.hnsw.efConstruction = self.config.hnsw_ef_construction
            self.index.hnsw.efSearch = self.config.hnsw_ef_search
        else:
            raise ValueError(f"Unsupported index type: {self.config.index_type}")
        
        logger.info(f"Created FAISS index: {self.index}")
    
    def add_vectors(self, vectors: np.ndarray, metadata: List[Dict[str, Any]]):
        """
        Add vectors and metadata to the index.
        
        Args:
            vectors: Numpy array of shape (n_vectors, vector_dimension)
            metadata: List of metadata dictionaries for each vector
        """
        if self.index is None:
            self.create_index(vectors.shape[1])
        
        # Normalize vectors if required
        if self.config.normalize_vectors:
            faiss.normalize_L2(vectors)
        
        # Add vectors to index
        self.index.add(vectors.astype('float32'))
        
        # Store metadata
        self.metadata.extend(metadata)
        
        logger.info(f"Added {len(vectors)} vectors to index. Total vectors: {self.index.ntotal}")
    
    def search(self, query_vector: np.ndarray, k: int = 10) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query vector of shape (vector_dimension,)
            k: Number of results to return
            
        Returns:
            Tuple of (distances, metadata_list)
        """
        if self.index is None:
            raise ValueError("Index not created. Call create_index() first.")
        
        # Normalize query vector if required
        if self.config.normalize_vectors:
            query_vector = query_vector.astype('float32')
            faiss.normalize_L2(query_vector.reshape(1, -1))
            query_vector = query_vector.reshape(-1)
        
        # Search
        distances, indices = self.index.search(query_vector.reshape(1, -1).astype('float32'), k)
        
        # Get metadata for results
        result_metadata = []
        for idx in indices[0]:
            if idx < len(self.metadata):
                result_metadata.append(self.metadata[idx])
            else:
                result_metadata.append({})
        
        return distances[0], result_metadata
    
    def save_index(self, index_path: str = None, metadata_path: str = None):
        """
        Save the index and metadata to disk.
        
        Args:
            index_path: Path to save the index file
            metadata_path: Path to save the metadata file
        """
        if self.index is None:
            raise ValueError("No index to save. Create and populate index first.")
        
        index_path = index_path or self.config.index_file
        metadata_path = metadata_path or self.config.metadata_file
        
        # Create directories if they don't exist
        Path(index_path).parent.mkdir(parents=True, exist_ok=True)
        Path(metadata_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, index_path)
        logger.info(f"Saved FAISS index to {index_path}")
        
        # Save metadata as JSONL
        with open(metadata_path, 'w', encoding='utf-8') as f:
            for meta in self.metadata:
                f.write(json.dumps(meta, ensure_ascii=False) + '\n')
        logger.info(f"Saved metadata to {metadata_path}")
    
    def load_index(self, index_path: str = None, metadata_path: str = None):
        """
        Load the index and metadata from disk.
        
        Args:
            index_path: Path to the index file
            metadata_path: Path to the metadata file
        """
        index_path = index_path or self.config.index_file
        metadata_path = metadata_path or self.config.metadata_file
        
        if not Path(index_path).exists():
            raise FileNotFoundError(f"Index file not found: {index_path}")
        if not Path(metadata_path).exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
        
        # Load FAISS index
        self.index = faiss.read_index(index_path)
        logger.info(f"Loaded FAISS index from {index_path}")
        
        # Load metadata
        self.metadata = []
        with open(metadata_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    self.metadata.append(json.loads(line.strip()))
        logger.info(f"Loaded {len(self.metadata)} metadata entries from {metadata_path}")
    
    def get_index_info(self) -> Dict[str, Any]:
        """Get information about the current index."""
        if self.index is None:
            return {"status": "No index loaded"}
        
        return {
            "index_type": self.config.index_type,
            "vector_dimension": self.vector_dimension,
            "total_vectors": self.index.ntotal,
            "metadata_entries": len(self.metadata),
            "is_trained": self.index.is_trained if hasattr(self.index, 'is_trained') else True
        }


class FAISSPipeline:
    """Pipeline for creating FAISS indexes from document chunks."""
    
    def __init__(self, config: FAISSConfig = None):
        """
        Initialize the FAISS pipeline.
        
        Args:
            config: FAISS configuration
        """
        self.config = config or FAISSConfig()
        self.indexer = FAISSIndexer(config)
        self.processed_chunks = 0
        self.total_vectors = 0
    
    def process_chunks_file(self, chunks_file: str, batch_size: int = 1000):
        """
        Process chunks from a JSONL file and create FAISS index.
        
        Args:
            chunks_file: Path to input JSONL file with chunks
            batch_size: Number of chunks to process in each batch
        """
        logger.info(f"Starting FAISS indexing for {chunks_file}")
        
        chunks_path = Path(chunks_file)
        if not chunks_path.exists():
            raise FileNotFoundError(f"Chunks file {chunks_file} not found")
        
        # Process chunks in batches
        batch_vectors = []
        batch_metadata = []
        
        with open(chunks_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(tqdm.tqdm(f, desc="Processing chunks")):
                if not line.strip():
                    continue
                
                try:
                    chunk = json.loads(line.strip())
                    
                    # Extract embedding if available
                    if 'embedding' in chunk:
                        embedding = np.array(chunk['embedding'], dtype='float32')
                        batch_vectors.append(embedding)
                        
                        # Create metadata entry
                        metadata = {
                            'chunk_id': chunk.get('chunk_id'),
                            'doc_id': chunk.get('doc_id'),
                            'chunk_index': chunk.get('chunk_index'),
                            'title': chunk.get('title'),
                            'authors': chunk.get('authors'),
                            'version': chunk.get('version'),
                            'text': chunk.get('text', '')[:500],  # Truncate for storage
                            'token_count': chunk.get('token_count'),
                            'char_count': chunk.get('char_count'),
                            'line_number': line_num + 1
                        }
                        batch_metadata.append(metadata)
                        
                        self.processed_chunks += 1
                        
                        # Process batch when it reaches batch_size
                        if len(batch_vectors) >= batch_size:
                            self.indexer.add_vectors(
                                np.array(batch_vectors), 
                                batch_metadata
                            )
                            self.total_vectors += len(batch_vectors)
                            batch_vectors = []
                            batch_metadata = []
                            
                except json.JSONDecodeError as e:
                    logger.warning(f"Error parsing line {line_num + 1}: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing chunk at line {line_num + 1}: {e}")
                    continue
        
        # Process remaining vectors
        if batch_vectors:
            self.indexer.add_vectors(
                np.array(batch_vectors), 
                batch_metadata
            )
            self.total_vectors += len(batch_vectors)
        
        # Save index and metadata
        self.indexer.save_index()
        
        logger.info(f"FAISS indexing completed!")
        logger.info(f"Processed chunks: {self.processed_chunks}")
        logger.info(f"Total vectors: {self.total_vectors}")
        logger.info(f"Index info: {self.indexer.get_index_info()}")
    
    def build_index_from_embeddings(self, embeddings: List[List[float]], metadata: List[Dict[str, Any]]):
        """
        Build FAISS index directly from embeddings and metadata.
        This is used in the hybrid workflow to create FAISS index from Pinecone data.
        
        Args:
            embeddings: List of embedding vectors
            metadata: List of metadata dictionaries
        """
        logger.info(f"Building FAISS index from {len(embeddings)} embeddings...")
        
        if not embeddings:
            logger.warning("No embeddings provided")
            return
        
        # Convert embeddings to numpy array
        vectors = np.array(embeddings, dtype='float32')
        
        # Add vectors to indexer
        self.indexer.add_vectors(vectors, metadata)
        self.total_vectors = len(embeddings)
        self.processed_chunks = len(metadata)
        
        # Save index and metadata
        self.indexer.save_index()
        
        logger.info(f"[OK] FAISS index built successfully!")
        logger.info(f"Total vectors: {self.total_vectors}")
        logger.info(f"Index info: {self.indexer.get_index_info()}")
    
    def search(self, query_vector: np.ndarray, k: int = 10) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Search the index for similar vectors.
        
        Args:
            query_vector: Query vector
            k: Number of results to return
            
        Returns:
            Tuple of (distances, metadata_list)
        """
        return self.indexer.search(query_vector, k)


def main():
    """Main function for testing FAISS indexing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Create FAISS index from chunks')
    parser.add_argument('--chunks-file', required=True, help='Input chunks JSONL file')
    parser.add_argument('--index-type', default='IndexFlatIP', 
                       choices=['IndexFlatIP', 'HNSW'], help='FAISS index type')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for processing')
    parser.add_argument('--vector-dimension', type=int, default=384, help='Vector dimension')
    
    args = parser.parse_args()
    
    # Create configuration
    config = FAISSConfig(
        index_type=args.index_type,
        vector_dimension=args.vector_dimension
    )
    
    # Create pipeline and process
    pipeline = FAISSPipeline(config)
    pipeline.process_chunks_file(args.chunks_file, args.batch_size)
    
    print("[OK] FAISS indexing completed!")


if __name__ == "__main__":
    main()
