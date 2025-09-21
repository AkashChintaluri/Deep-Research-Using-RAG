#!/usr/bin/env python3
"""
Sync Pinecone to FAISS Script
============================

This script retrieves embeddings from Pinecone and creates/updates a local FAISS index.
This is useful for the hybrid workflow where Pinecone is used for storage and FAISS for search.

Usage:
    python scripts/sync_pinecone_to_faiss.py --api-key "your-key" --index "arxiv-papers"
    python scripts/sync_pinecone_to_faiss.py --api-key "your-key" --index "arxiv-papers" --batch-size 1000
    python scripts/sync_pinecone_to_faiss.py --api-key "your-key" --index "arxiv-papers" --chunks-file "data/processed/arxiv_chunks.jsonl"
"""

import sys
import os
import argparse
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from services.pinecone_integration import PineconePipeline, PineconeConfig
from services.faiss_indexing import FAISSPipeline, FAISSConfig
from core.config import Config

def sync_pinecone_to_faiss(api_key: str, index_name: str, environment: str = None, 
                          chunks_file: str = None, batch_size: int = 1000):
    """
    Retrieve embeddings from Pinecone and create FAISS index.
    
    Args:
        api_key: Pinecone API key
        index_name: Pinecone index name
        environment: Pinecone environment
        chunks_file: Path to chunks file for metadata
        batch_size: Batch size for retrieval
    """
    print("🔄 Syncing Pinecone to FAISS")
    print("=" * 50)
    
    # Create Pinecone configuration
    pinecone_config = PineconeConfig(
        api_key=api_key,
        index_name=index_name,
        environment=environment or Config.PINECONE_ENVIRONMENT
    )
    
    # Create Pinecone pipeline
    pinecone_pipeline = PineconePipeline(pinecone_config)
    
    # Create FAISS configuration
    faiss_config = FAISSConfig(
        index_type=Config.FAISS_INDEX_TYPE,
        vector_dimension=Config.PINECONE_DIMENSION,
        metadata_file=Config.FAISS_METADATA_FILE,
        index_file=Config.FAISS_INDEX_FILE,
        normalize_vectors=Config.EMBEDDING_NORMALIZE_VECTORS
    )
    
    # Create FAISS pipeline
    faiss_pipeline = FAISSPipeline(faiss_config)
    
    try:
        # Get index stats
        stats = pinecone_pipeline.index.describe_index_stats()
        total_vectors = stats['total_vector_count']
        print(f"📊 Pinecone index stats:")
        print(f"   Total vectors: {total_vectors}")
        print(f"   Index name: {index_name}")
        print()
        
        if total_vectors == 0:
            print("❌ No vectors found in Pinecone index")
            return
        
        # Read chunks for metadata if provided
        chunks_metadata = {}
        if chunks_file and Path(chunks_file).exists():
            print(f"📖 Reading metadata from {chunks_file}...")
            with open(chunks_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        chunk = eval(line.strip())  # Use eval for JSON parsing
                        chunks_metadata[chunk['chunk_id']] = chunk
            print(f"   Loaded metadata for {len(chunks_metadata)} chunks")
        
        # Retrieve all vectors from Pinecone
        print(f"🔄 Retrieving vectors from Pinecone in batches of {batch_size}...")
        
        all_embeddings = []
        all_metadata = []
        
        # Get all vector IDs first
        vector_ids = []
        for namespace in stats['namespaces']:
            namespace_stats = stats['namespaces'][namespace]
            if namespace_stats['vector_count'] > 0:
                # Query to get vector IDs (this is a simplified approach)
                # In practice, you might need to use list_vectors or query with include_metadata=True
                print(f"   Processing namespace: {namespace} ({namespace_stats['vector_count']} vectors)")
        
        # For now, we'll use a different approach - query with include_metadata=True
        # to get all vectors. This is not the most efficient but works for demonstration
        print("   Note: This is a simplified retrieval. For production, consider using list_vectors API.")
        
        # Create a dummy query to retrieve vectors (this is a workaround)
        # In practice, you'd want to use the list_vectors API when available
        dummy_query = [0.0] * Config.PINECONE_DIMENSION
        results = pinecone_pipeline.index.query(
            vector=dummy_query,
            top_k=min(10000, total_vectors),  # Limit for demo
            include_metadata=True
        )
        
        print(f"   Retrieved {len(results['matches'])} vectors")
        
        # Process retrieved vectors
        for match in results['matches']:
            vector_id = match['id']
            embedding = match['values']
            metadata = match.get('metadata', {})
            
            all_embeddings.append(embedding)
            
            # Use chunks metadata if available, otherwise use Pinecone metadata
            if vector_id in chunks_metadata:
                chunk_data = chunks_metadata[vector_id]
                faiss_metadata = {
                    'chunk_id': vector_id,
                    'doc_id': chunk_data.get('doc_id', ''),
                    'text': chunk_data.get('text', '')[:500],  # Truncate for storage
                    'title': chunk_data.get('title', ''),
                    'authors': chunk_data.get('authors', ''),
                    'version': chunk_data.get('version', ''),
                    'token_count': chunk_data.get('token_count', 0),
                    'char_count': chunk_data.get('char_count', 0)
                }
            else:
                faiss_metadata = {
                    'chunk_id': vector_id,
                    'doc_id': metadata.get('doc_id', ''),
                    'text': metadata.get('text', '')[:500],
                    'title': metadata.get('title', ''),
                    'authors': metadata.get('authors', ''),
                    'version': metadata.get('version', ''),
                    'token_count': metadata.get('token_count', 0),
                    'char_count': metadata.get('char_count', 0)
                }
            
            all_metadata.append(faiss_metadata)
        
        # Build FAISS index
        print(f"\n🔍 Building FAISS index with {len(all_embeddings)} vectors...")
        faiss_pipeline.build_index_from_embeddings(all_embeddings, all_metadata)
        
        print("✅ Sync completed successfully!")
        print(f"   FAISS index: {Config.FAISS_INDEX_FILE}")
        print(f"   FAISS metadata: {Config.FAISS_METADATA_FILE}")
        
    except Exception as e:
        print(f"❌ Error syncing Pinecone to FAISS: {e}")
        raise

def main():
    """Main function for syncing Pinecone to FAISS."""
    parser = argparse.ArgumentParser(description='Sync Pinecone embeddings to FAISS index')
    
    # Required arguments
    parser.add_argument('--api-key', required=True, help='Pinecone API key')
    parser.add_argument('--index', required=True, help='Pinecone index name')
    
    # Optional arguments
    parser.add_argument('--environment', default=Config.PINECONE_ENVIRONMENT, 
                       help='Pinecone environment')
    parser.add_argument('--chunks-file', default='data/processed/arxiv_chunks.jsonl',
                       help='Path to chunks file for metadata')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Batch size for retrieval')
    
    args = parser.parse_args()
    
    # Validate chunks file
    if not Path(args.chunks_file).exists():
        print(f"⚠️  Warning: Chunks file {args.chunks_file} not found")
        print("   Metadata will be limited to what's stored in Pinecone")
        args.chunks_file = None
    
    sync_pinecone_to_faiss(
        api_key=args.api_key,
        index_name=args.index,
        environment=args.environment,
        chunks_file=args.chunks_file,
        batch_size=args.batch_size
    )

if __name__ == "__main__":
    main()
