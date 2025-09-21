#!/usr/bin/env python3
"""
Pinecone Search Script
======================

This script provides a simple interface for searching the Pinecone index.

Usage:
    python scripts/search_pinecone.py --query "machine learning"
    python scripts/search_pinecone.py --query "quantum computing" --n-results 5
    python scripts/search_pinecone.py --info
"""

import sys
import argparse
import numpy as np
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from services.pinecone_integration import PineconePipeline, PineconeConfig
from services.embedding_generation import EmbeddingGenerator, EmbeddingConfig
from core.config import Config

def main():
    """Main function for Pinecone search."""
    parser = argparse.ArgumentParser(description='Search Pinecone index')
    parser.add_argument('--query', '-q', help='Search query')
    parser.add_argument('--n-results', '-n', type=int, default=10, 
                       help='Number of results to return (default: 10)')
    parser.add_argument('--doc-id', help='Filter by document ID')
    parser.add_argument('--author', help='Filter by author name')
    parser.add_argument('--title', help='Filter by title')
    parser.add_argument('--info', action='store_true', help='Show index information')
    parser.add_argument('--api-key', help='Pinecone API key')
    parser.add_argument('--index-name', help='Pinecone index name')
    parser.add_argument('--environment', help='Pinecone environment')
    
    args = parser.parse_args()
    
    # Create configuration (use Config defaults if not provided)
    config = PineconeConfig(
        api_key=args.api_key or Config.PINECONE_API_KEY,
        index_name=args.index_name or Config.PINECONE_INDEX_NAME,
        environment=args.environment or Config.PINECONE_ENVIRONMENT
    )
    
    # Validate configuration
    if not config.api_key:
        print("❌ Error: Pinecone API key must be provided!")
        print("Set PINECONE_API_KEY in your .env file or use --api-key")
        return
    
    # Create pipeline
    pipeline = PineconePipeline(config)
    
    try:
        # Connect to Pinecone
        pipeline.manager.connect()
        
        if args.info:
            # Show index information
            stats = pipeline.manager.get_index_stats()
            print("=" * 50)
            print("Pinecone Index Information")
            print("=" * 50)
            for key, value in stats.items():
                print(f"{key}: {value}")
            print("=" * 50)
            
        elif args.query:
            # Search
            print(f"Searching for: '{args.query}'")
            print(f"Results: {args.n_results}")
            print("-" * 50)
            
            # Generate embedding for query
            embedding_config = EmbeddingConfig(
                model_name=Config.EMBEDDING_MODEL_NAME,
                normalize_vectors=Config.EMBEDDING_NORMALIZE_VECTORS
            )
            generator = EmbeddingGenerator(embedding_config)
            generator.load_model()
            
            query_embedding = generator.generate_embedding(args.query)
            
            # Build filters
            filters = {}
            if args.doc_id:
                filters['doc_id'] = args.doc_id
            if args.author:
                filters['authors'] = args.author
            if args.title:
                filters['title'] = args.title
            
            # Search Pinecone
            results = pipeline.search(query_embedding, args.n_results, filters)
            
            # Display results
            if not results:
                print("No results found.")
                return
            
            for i, result in enumerate(results):
                metadata = result.get('metadata', {})
                print(f"\n{i+1}. Similarity: {result.get('score', 'N/A'):.4f}")
                print(f"   Vector ID: {result.get('id', 'Unknown')}")
                print(f"   Document ID: {metadata.get('doc_id', 'Unknown')}")
                print(f"   Title: {metadata.get('title', 'Unknown')}")
                print(f"   Authors: {metadata.get('authors', 'Unknown')}")
                print(f"   Text: {metadata.get('text', '')[:200]}...")
                print(f"   Token Count: {metadata.get('token_count', 'Unknown')}")
                print("-" * 50)
        
        else:
            print("❌ Error: You must specify --query or --info")
            parser.print_help()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return

if __name__ == "__main__":
    main()
