#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAISS Search Script
==================

Search the local FAISS index for similar chunks.
"""

import sys
import argparse
import os
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from services.embedding_generation import EmbeddingPipeline, EmbeddingConfig
from core.config import Config

def search_faiss(query: str, n_results: int = 5):
    """Search FAISS index."""
    config = EmbeddingConfig(
        model_name=Config.EMBEDDING_MODEL_NAME,
        use_faiss=True,
        faiss_index_file=os.path.join(Config.PROCESSED_DATA_DIR, 'faiss_index.bin'),
        faiss_metadata_file=os.path.join(Config.PROCESSED_DATA_DIR, 'faiss_metadata.jsonl')
    )
    
    pipeline = EmbeddingPipeline(config)
    results = pipeline.search_faiss(query, n_results)
    
    print(f"Search Results for: '{query}'")
    print("=" * 50)
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result['score']:.4f}")
        print(f"   Paper ID: {result['doc_id']}")
        print(f"   Chunk: {result['chunk_id']}")
        print(f"   Text: {result['text'][:200]}...")
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Search FAISS index')
    parser.add_argument('--query', '-q', required=True, help='Search query')
    parser.add_argument('--n-results', '-n', type=int, default=5, help='Number of results')
    
    args = parser.parse_args()
    search_faiss(args.query, args.n_results)
