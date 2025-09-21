#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pinecone Vector Search Script
============================

Search the Pinecone vector database for similar chunks using semantic search.
"""

import sys
import argparse
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from services.embedding_generation import EmbeddingPipeline, EmbeddingConfig
from core.config import Config

def search_pinecone(query: str, n_results: int = 5):
    """Search Pinecone vector database."""
    try:
        from services.pinecone_integration import PineconePipeline, PineconeConfig
        
        # Create Pinecone pipeline
        config = PineconeConfig(
            api_key=Config.PINECONE_API_KEY,
            index_name=Config.PINECONE_INDEX_NAME,
            environment=Config.PINECONE_ENVIRONMENT
        )
        
        pipeline = PineconePipeline(config)
        pipeline.manager.connect()
        
        # Generate query embedding
        from services.embedding_generation import EmbeddingGenerator, EmbeddingConfig
        embedding_config = EmbeddingConfig(model_name=Config.EMBEDDING_MODEL_NAME)
        generator = EmbeddingGenerator(embedding_config)
        query_embedding = generator.generate_embedding(query)
        
        # Search Pinecone
        search_results = pipeline.manager.index.query(
            vector=query_embedding.tolist(),
            top_k=n_results,
            include_metadata=True
        )
        
        # Format results
        results = []
        for match in search_results.matches:
            result = {
                'doc_id': match.metadata.get('doc_id', 'Unknown'),
                'chunk_id': match.metadata.get('chunk_id', 'Unknown'),
                'score': match.score,
                'text': match.metadata.get('text', 'No text')[:200] + '...' if match.metadata.get('text') else 'No text'
            }
            results.append(result)
        
        print(f"Pinecone Vector Search Results for: '{query}'")
        print("=" * 60)
        print(f"Found {len(results)} results")
        print()
        
        for i, result in enumerate(results, 1):
            print(f"{i}. Paper ID: {result.get('doc_id', 'Unknown')}")
            print(f"   Chunk ID: {result.get('chunk_id', 'Unknown')}")
            print(f"   Score: {result.get('score', 0):.4f}")
            print(f"   Text: {result.get('text', 'No text')}")
            print("-" * 60)
        
        return results
        
    except Exception as e:
        print(f"Error searching Pinecone: {e}")
        print("Make sure the pipeline has completed and Pinecone index is populated.")
        import traceback
        traceback.print_exc()
        return []

def search_faiss(query: str, n_results: int = 5):
    """Search local FAISS index."""
    try:
        # Create embedding pipeline with FAISS
        config = EmbeddingConfig(
            model_name=Config.EMBEDDING_MODEL_NAME,
            use_faiss=True,
            faiss_index_file=os.path.join(Config.PROCESSED_DATA_DIR, 'faiss_index.bin'),
            faiss_metadata_file=os.path.join(Config.PROCESSED_DATA_DIR, 'faiss_metadata.jsonl')
        )
        
        pipeline = EmbeddingPipeline(config)
        
        # Search FAISS
        results = pipeline.search_faiss(query, n_results)
        
        print(f"FAISS Vector Search Results for: '{query}'")
        print("=" * 60)
        print(f"Found {len(results)} results")
        print()
        
        for i, result in enumerate(results, 1):
            print(f"{i}. Paper ID: {result.get('doc_id', 'Unknown')}")
            print(f"   Chunk ID: {result.get('chunk_id', 'Unknown')}")
            print(f"   Score: {result.get('score', 0):.4f}")
            print(f"   Text: {result.get('text', 'No text')[:200]}...")
            print("-" * 60)
        
        return results
        
    except Exception as e:
        print(f"Error searching FAISS: {e}")
        print("Make sure the FAISS index has been created.")
        return []

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Search vector databases')
    
    # Search options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--pinecone', action='store_true', help='Search Pinecone vector database')
    group.add_argument('--faiss', action='store_true', help='Search local FAISS index')
    
    parser.add_argument('--query', '-q', required=True, help='Search query')
    parser.add_argument('--n-results', '-n', type=int, default=5, help='Number of results to show')
    
    args = parser.parse_args()
    
    if args.pinecone:
        search_pinecone(args.query, args.n_results)
    elif args.faiss:
        search_faiss(args.query, args.n_results)

if __name__ == "__main__":
    main()
