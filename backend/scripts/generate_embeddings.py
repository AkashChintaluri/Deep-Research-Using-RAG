#!/usr/bin/env python3
"""
Generate Embeddings Script
=========================

Generate embeddings for existing chunks and store in Pinecone + FAISS.
This script assumes chunks already exist in processed_data/arxiv_chunks.jsonl.
"""

import sys
import argparse
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_dir))

from services.embedding_generation import EmbeddingPipeline, EmbeddingConfig
from core.config import Config

def main():
    parser = argparse.ArgumentParser(description='Generate embeddings for existing chunks')
    parser.add_argument('--chunks-file', default='data/processed/arxiv_chunks.jsonl', 
                       help='Path to chunks file')
    parser.add_argument('--output-file', default='data/processed/arxiv_embeddings.jsonl',
                       help='Path to output embeddings file')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Batch size for processing')
    parser.add_argument('--workers', type=int, default=1,
                       help='Number of workers (use 1 to avoid multiprocessing issues)')
    parser.add_argument('--pinecone', action='store_true',
                       help='Enable Pinecone storage')
    
    args = parser.parse_args()
    
    # Check if chunks file exists
    chunks_path = Path(args.chunks_file)
    if not chunks_path.exists():
        print(f"Error: Chunks file {args.chunks_file} not found!")
        print("Run the chunking step first: python scripts/complete_pipeline.py --limit 0")
        return 1
    
    # Create embedding configuration
    config = EmbeddingConfig(
        model_name=Config.EMBEDDING_MODEL_NAME,
        batch_size=args.batch_size,
        max_workers=args.workers,
        normalize_vectors=Config.EMBEDDING_NORMALIZE_VECTORS,
        use_faiss=True,
        faiss_index_type='IndexFlatIP',
        faiss_metadata_file='processed_data/faiss_metadata.jsonl',
        faiss_index_file='processed_data/faiss_index.bin',
        use_pinecone=args.pinecone,
        pinecone_api_key=Config.PINECONE_API_KEY,
        pinecone_index_name=Config.PINECONE_INDEX_NAME,
        pinecone_environment=Config.PINECONE_ENVIRONMENT
    )
    
    # Create pipeline
    pipeline = EmbeddingPipeline(config)
    
    print(f"🚀 Starting embedding generation...")
    print(f"   Chunks file: {args.chunks_file}")
    print(f"   Output file: {args.output_file}")
    print(f"   Batch size: {args.batch_size}")
    print(f"   Workers: {args.workers}")
    print(f"   Pinecone: {'Enabled' if args.pinecone else 'Disabled'}")
    print()
    
    try:
        if args.pinecone:
            # Use hybrid workflow
            pipeline.process_chunks_file_with_pinecone(
                args.chunks_file, 
                args.output_file, 
                batch_size=args.batch_size
            )
        else:
            # Just generate embeddings
            pipeline.process_chunks_file(
                args.chunks_file, 
                args.output_file, 
                batch_size=args.batch_size
            )
        
        print("✅ Embedding generation completed successfully!")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
