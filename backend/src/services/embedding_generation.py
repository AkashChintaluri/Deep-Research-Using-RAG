#!/usr/bin/env python3
"""
Embedding Generation Module for ArXiv Data Processing
====================================================

This module handles generating embeddings for document chunks using local models.
It supports sentence-transformers models and stores embeddings in PostgreSQL.

Key Features:
- Local embedding generation (no API calls)
- Support for multiple embedding models
- Vector normalization for cosine similarity
- Batch processing for efficiency
- PostgreSQL storage with pgvector support
- Parallel processing for large datasets
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
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
from .faiss_indexing import FAISSPipeline, FAISSConfig
from .pinecone_integration import PineconePipeline, PineconeConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('embedding_generation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""
    model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'
    batch_size: int = 32
    max_workers: int = None
    normalize_vectors: bool = True
    vector_dimension: int = 384  # all-MiniLM-L6-v2 dimension
    # FAISS configuration
    use_faiss: bool = True  # Create FAISS index
    faiss_index_type: str = 'IndexFlatIP'  # IndexFlatIP, HNSW
    faiss_metadata_file: str = None
    faiss_index_file: str = None
    # Pinecone configuration
    use_pinecone: bool = True  # Store in Pinecone
    pinecone_api_key: str = None
    pinecone_index_name: str = None
    pinecone_environment: str = None


class EmbeddingGenerator:
    """Handles embedding generation for document chunks."""
    
    def __init__(self, config: EmbeddingConfig = None):
        """
        Initialize the embedding generator.
        
        Args:
            config: Embedding configuration
        """
        self.config = config or EmbeddingConfig()
        self.model = None
        self.processed_chunks = 0
        self.total_embeddings = 0
        
        # Set max workers if not specified
        if self.config.max_workers is None:
            self.config.max_workers = min(cpu_count(), 4)  # Cap at 4 for memory efficiency
    
    def load_model(self):
        """Load the embedding model."""
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self.config.model_name}")
            self.model = SentenceTransformer(self.config.model_name)
            logger.info(f"Model loaded successfully. Vector dimension: {self.model.get_sentence_embedding_dimension()}")
            
            # Update config with actual dimension
            self.config.vector_dimension = self.model.get_sentence_embedding_dimension()
            
        except ImportError:
            logger.error("sentence-transformers not installed. Please install with: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Normalized embedding vector
        """
        if not self.model:
            self.load_model()
        
        # Generate embedding
        embedding = self.model.encode([text], convert_to_tensor=False)[0]
        
        # Normalize for cosine similarity
        if self.config.normalize_vectors:
            embedding = embedding / np.linalg.norm(embedding)
        
        return embedding.astype(np.float32)
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of normalized embedding vectors
        """
        if not self.model:
            self.load_model()
        
        # Generate embeddings
        embeddings = self.model.encode(texts, convert_to_tensor=False, batch_size=self.config.batch_size)
        
        # Normalize for cosine similarity
        if self.config.normalize_vectors:
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        return [emb.astype(np.float32) for emb in embeddings]


def process_chunks_parallel(args):
    """Parallel processing function for generating embeddings."""
    chunks_batch, config_dict = args
    
    # Recreate config from dict
    config = EmbeddingConfig(**config_dict)
    generator = EmbeddingGenerator(config)
    generator.load_model()
    
    # Extract texts from chunks
    texts = [chunk['text'] for chunk in chunks_batch]
    
    # Generate embeddings
    embeddings = generator.generate_embeddings_batch(texts)
    
    # Combine chunks with embeddings
    results = []
    for chunk, embedding in zip(chunks_batch, embeddings):
        result = chunk.copy()
        result['embedding'] = embedding.tolist()  # Convert numpy array to list for JSON serialization
        results.append(result)
    
    return results


class EmbeddingPipeline:
    """Pipeline for generating embeddings from chunks."""
    
    def __init__(self, config: EmbeddingConfig = None):
        """
        Initialize the embedding pipeline.
        
        Args:
            config: Embedding configuration
        """
        self.config = config or EmbeddingConfig()
        self.generator = EmbeddingGenerator(config)
        self.processed_chunks = 0
        self.total_embeddings = 0
    
    def process_chunks_file(self, input_file: str, output_file: str, 
                           batch_size: int = 1000) -> None:
        """
        Process chunks from a JSONL file and generate embeddings.
        
        Args:
            input_file: Path to input JSONL file with chunks
            output_file: Path to output JSONL file with embeddings
            batch_size: Number of chunks to process in each batch
        """
        logger.info(f"Starting embedding generation for {input_file}")
        
        input_path = Path(input_file)
        output_path = Path(output_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file {input_file} not found")
        
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load model
        self.generator.load_model()
        
        # Read all chunks
        chunks = []
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    chunks.append(json.loads(line.strip()))
        
        total_chunks = len(chunks)
        logger.info(f"Processing {total_chunks} chunks with {self.config.max_workers} workers")
        
        # Process chunks in parallel batches
        config_dict = {
            'model_name': self.config.model_name,
            'batch_size': self.config.batch_size,
            'max_workers': self.config.max_workers,
            'normalize_vectors': self.config.normalize_vectors,
            'vector_dimension': self.config.vector_dimension
        }
        
        with open(output_path, 'w', encoding='utf-8') as outfile:
            with tqdm.tqdm(total=total_chunks, desc="Generating embeddings") as pbar:
                # Process in batches
                for i in range(0, total_chunks, batch_size):
                    batch_chunks = chunks[i:i + batch_size]
                    
                    # Split batch into smaller chunks for parallel processing
                    chunk_size = max(1, len(batch_chunks) // self.config.max_workers)
                    parallel_batches = [batch_chunks[j:j + chunk_size] for j in range(0, len(batch_chunks), chunk_size)]
                    
                    # Process parallel batches
                    with ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
                        # Submit all tasks
                        future_to_batch = {executor.submit(process_chunks_parallel, (batch, config_dict)): batch for batch in parallel_batches}
                        
                        # Process completed tasks
                        for future in as_completed(future_to_batch):
                            results = future.result()
                            
                            # Write results to output file
                            for result in results:
                                outfile.write(json.dumps(result, ensure_ascii=False) + '\n')
                                self.processed_chunks += 1
                                self.total_embeddings += 1
                            
                            pbar.update(len(results))
                            
                            # Log progress
                            if self.processed_chunks % 1000 == 0:
                                logger.info(f"Processed {self.processed_chunks} chunks, generated {self.total_embeddings} embeddings")
        
        logger.info(f"Embedding generation completed!")
        logger.info(f"Processed chunks: {self.processed_chunks}")
        logger.info(f"Total embeddings: {self.total_embeddings}")
        logger.info(f"Output file: {output_path}")
        logger.info(f"Vector dimension: {self.config.vector_dimension}")
    
    def process_chunks_from_database(self, db_manager, output_file: str, 
                                   batch_size: int = 1000, limit: int = None) -> None:
        """
        Process chunks directly from PostgreSQL database and generate embeddings.
        
        Args:
            db_manager: PostgreSQL database manager
            output_file: Path to output JSONL file with embeddings
            batch_size: Number of chunks to process in each batch
            limit: Maximum number of chunks to process (None for all)
        """
        logger.info(f"Starting embedding generation from database")
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load model
        self.generator.load_model()
        
        # Get total chunk count
        db_manager.cursor.execute("SELECT COUNT(*) as total FROM papers")
        total_chunks = db_manager.cursor.fetchone()['total']
        
        if limit:
            total_chunks = min(total_chunks, limit)
        
        logger.info(f"Processing {total_chunks} chunks with {self.config.max_workers} workers")
        
        with open(output_path, 'w', encoding='utf-8') as outfile:
            with tqdm.tqdm(total=total_chunks, desc="Generating embeddings") as pbar:
                offset = 0
                
                while offset < total_chunks:
                    # Fetch batch of documents
                    query = """
                        SELECT id, title, authors, abstract, body, version
                        FROM papers 
                        ORDER BY id 
                        LIMIT %s OFFSET %s
                    """
                    db_manager.cursor.execute(query, (batch_size, offset))
                    documents = db_manager.cursor.fetchall()
                    
                    if not documents:
                        break
                    
                    # Convert to chunks (simplified - in practice you'd want to use actual chunks)
                    chunks = []
                    for doc in documents:
                        document = dict(doc)
                        # Create a simple chunk from abstract
                        chunk = {
                            'doc_id': document['id'],
                            'chunk_id': f"{document['id']}_chunk_0",
                            'text': document.get('abstract', ''),
                            'title': document.get('title', ''),
                            'authors': document.get('authors', ''),
                            'version': document.get('version', '')
                        }
                        chunks.append(chunk)
                    
                    # Generate embeddings for this batch
                    texts = [chunk['text'] for chunk in chunks]
                    embeddings = self.generator.generate_embeddings_batch(texts)
                    
                    # Write results
                    for chunk, embedding in zip(chunks, embeddings):
                        result = chunk.copy()
                        result['embedding'] = embedding.tolist()
                        outfile.write(json.dumps(result, ensure_ascii=False) + '\n')
                        self.processed_chunks += 1
                        self.total_embeddings += 1
                    
                    pbar.update(len(chunks))
                    offset += batch_size
                    
                    # Log progress
                    if self.processed_chunks % 1000 == 0:
                        logger.info(f"Processed {self.processed_chunks} chunks, generated {self.total_embeddings} embeddings")
        
        logger.info(f"Database embedding generation completed!")
        logger.info(f"Processed chunks: {self.processed_chunks}")
        logger.info(f"Total embeddings: {self.total_embeddings}")
        logger.info(f"Output file: {output_path}")
        logger.info(f"Vector dimension: {self.config.vector_dimension}")
    
    def create_faiss_index(self, chunks_file: str, batch_size: int = 1000):
        """
        Create FAISS index from chunks file.
        
        Args:
            chunks_file: Path to input JSONL file with chunks
            batch_size: Number of chunks to process in each batch
        """
        if not self.config.use_faiss:
            logger.info("FAISS indexing disabled in configuration")
            return
        
        try:
            logger.info("Creating FAISS index...")
            
            # Create FAISS configuration
            faiss_config = FAISSConfig(
                index_type=self.config.faiss_index_type,
                vector_dimension=self.config.vector_dimension,
                metadata_file=self.config.faiss_metadata_file,
                index_file=self.config.faiss_index_file,
                normalize_vectors=self.config.normalize_vectors
            )
            
            # Create FAISS pipeline and process
            faiss_pipeline = FAISSPipeline(faiss_config)
            faiss_pipeline.process_chunks_file(chunks_file, batch_size)
            
            logger.info("[OK] FAISS index created successfully!")
        except ImportError as e:
            logger.warning(f"FAISS not available: {e}")
            logger.info("Skipping FAISS indexing. Install with: pip install faiss-cpu")
        except Exception as e:
            logger.error(f"Error creating FAISS index: {e}")
            logger.info("Continuing without FAISS indexing...")
    
    def process_chunks_file_with_pinecone(self, input_file: str, output_file: str = None, 
                                        batch_size: int = 1000) -> None:
        """
        Process chunks from a JSONL file, generate embeddings, and store in Pinecone.
        This method implements the hybrid workflow: Pinecone for storage, FAISS for search.
        
        Args:
            input_file: Path to input JSONL file with chunks
            output_file: Path to output JSONL file with embeddings (optional)
            batch_size: Number of chunks to process in each batch
        """
        if not self.config.use_pinecone:
            logger.info("Pinecone storage disabled in configuration")
            return
        
        try:
            logger.info("Starting hybrid workflow: Pinecone storage + FAISS search...")
            
            # Step 1: Generate embeddings for all chunks
            logger.info("Step 1: Generating embeddings for all chunks...")
            embeddings_file = output_file or str(Path(input_file).with_suffix('.embeddings.jsonl'))
            self.process_chunks_file(input_file, embeddings_file, batch_size)
            
            # Step 2: Store embeddings in Pinecone
            logger.info("Step 2: Storing embeddings in Pinecone...")
            pinecone_config = PineconeConfig(
                api_key=self.config.pinecone_api_key,
                index_name=self.config.pinecone_index_name,
                environment=self.config.pinecone_environment
            )
            
            pinecone_pipeline = PineconePipeline(pinecone_config)
            pinecone_pipeline.process_chunks_file(embeddings_file, batch_size)
            
            # Step 3: Create FAISS index from Pinecone
            logger.info("Step 3: Creating FAISS index from Pinecone...")
            self._create_faiss_from_pinecone(pinecone_pipeline, embeddings_file, batch_size)
            
            logger.info("[OK] Hybrid workflow completed!")
            logger.info(f"Processed chunks: {pinecone_pipeline.processed_documents}")
            logger.info("[OK] Pinecone: Used for persistent storage")
            logger.info("[OK] FAISS: Used for fast local search")
            
        except ImportError as e:
            logger.warning(f"Pinecone not available: {e}")
            logger.info("Skipping Pinecone storage. Install with: pip install pinecone-client")
        except Exception as e:
            logger.error(f"Error with hybrid workflow: {e}")
            logger.info("Continuing without Pinecone storage...")
    
    def _create_faiss_from_pinecone(self, pinecone_pipeline, input_file: str, batch_size: int = 1000):
        """
        Retrieve embeddings from Pinecone and create FAISS index for local search.
        
        Args:
            pinecone_pipeline: Initialized Pinecone pipeline
            input_file: Path to input JSONL file with chunks
            batch_size: Number of chunks to process in each batch
        """
        if not self.config.use_faiss:
            logger.info("FAISS indexing disabled in configuration")
            return
        
        try:
            logger.info("Retrieving embeddings from Pinecone to create FAISS index...")
            
            # Read chunks to get metadata
            chunks = []
            with open(input_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        chunks.append(json.loads(line.strip()))
            
            # Retrieve embeddings from Pinecone in batches
            all_embeddings = []
            all_metadata = []
            
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]
                chunk_ids = [chunk['chunk_id'] for chunk in batch_chunks]
                
                # Retrieve embeddings from Pinecone
                results = pinecone_pipeline.index.fetch(ids=chunk_ids)
                
                for chunk_id in chunk_ids:
                    if chunk_id in results['vectors']:
                        vector_data = results['vectors'][chunk_id]
                        embedding = vector_data['values']
                        metadata = vector_data.get('metadata', {})
                        
                        all_embeddings.append(embedding)
                        all_metadata.append({
                            'chunk_id': chunk_id,
                            'doc_id': metadata.get('doc_id', ''),
                            'text': metadata.get('text', ''),
                            'title': metadata.get('title', ''),
                            'authors': metadata.get('authors', ''),
                            'version': metadata.get('version', '')
                        })
                
                logger.info(f"Retrieved {len(all_embeddings)} embeddings from Pinecone...")
            
            # Create FAISS index with retrieved embeddings
            if all_embeddings:
                logger.info("Creating FAISS index with retrieved embeddings...")
                
                # Create FAISS configuration
                faiss_config = FAISSConfig(
                    index_type=self.config.faiss_index_type,
                    vector_dimension=self.config.vector_dimension,
                    metadata_file=self.config.faiss_metadata_file,
                    index_file=self.config.faiss_index_file,
                    normalize_vectors=self.config.normalize_vectors
                )
                
                # Create FAISS pipeline and build index
                faiss_pipeline = FAISSPipeline(faiss_config)
                faiss_pipeline.build_index_from_embeddings(all_embeddings, all_metadata)
                
                logger.info("[OK] FAISS index created successfully from Pinecone embeddings!")
            else:
                logger.warning("No embeddings retrieved from Pinecone")
                
        except Exception as e:
            logger.error(f"Error creating FAISS from Pinecone: {e}")
            logger.info("Continuing without FAISS index...")
    


def main():
    """Main function for running embedding generation."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate embeddings for document chunks')
    parser.add_argument('--input', '-i', required=True, help='Input JSONL file with chunks')
    parser.add_argument('--output', '-o', required=True, help='Output JSONL file with embeddings')
    parser.add_argument('--model', default='sentence-transformers/all-MiniLM-L6-v2', 
                       help='Embedding model name')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size for embedding generation')
    parser.add_argument('--max-workers', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--no-normalize', action='store_true', help='Skip vector normalization')
    
    args = parser.parse_args()
    
    # Create configuration
    config = EmbeddingConfig(
        model_name=args.model,
        batch_size=args.batch_size,
        max_workers=args.max_workers,
        normalize_vectors=not args.no_normalize
    )
    
    # Create and run pipeline
    pipeline = EmbeddingPipeline(config)
    pipeline.process_chunks_file(args.input, args.output)


if __name__ == "__main__":
    main()
