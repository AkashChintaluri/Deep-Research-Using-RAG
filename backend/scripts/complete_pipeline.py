#!/usr/bin/env python3
"""
Complete RAG Pipeline for ArXiv PDFs
===================================

This script processes PDFs through the complete RAG pipeline:
1. Extract text from PDFs and store in database
2. Chunk the papers into searchable segments
3. Generate embeddings for all chunks
4. Store embeddings in Pinecone
5. Create FAISS index for fast local search

Usage:
    python scripts/complete_pipeline.py --limit 10  # Test with 10 PDFs
    python scripts/complete_pipeline.py             # Process all PDFs
"""

import sys
import os
import argparse
from pathlib import Path
import time

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from services.pdf_processor import PDFProcessor
from services.document_chunking import ChunkingPipeline, ChunkConfig
from services.embedding_generation import EmbeddingPipeline, EmbeddingConfig
from services.data_ingestion_postgres import PostgreSQLManager
from core.config import Config


def process_pdfs(pdf_dir: str, db_config: dict, limit: int = None):
    """Step 1: Process PDFs and extract text."""
    print("\n" + "="*60)
    print("📄 STEP 1: PDF Processing & Text Extraction")
    print("="*60)
    
    processor = PDFProcessor(pdf_dir, db_config)
    processor.process_all_pdfs(limit)
    
    print(f"✅ PDF Processing Complete!")
    print(f"   Processed: {processor.processed_count} PDFs")
    print(f"   Errors: {processor.error_count}")
    print(f"   Total text: {processor.total_text_length:,} characters")
    
    return processor.processed_count


def chunk_papers(db_config: dict, limit: int = None):
    """Step 2: Chunk papers into searchable segments."""
    print("\n" + "="*60)
    print("✂️  STEP 2: Document Chunking")
    print("="*60)
    
    # Chunking configuration
    config = ChunkConfig(
        min_chunk_size=200,
        max_chunk_size=600,
        overlap_size=75,
        chunk_field='full_text',  # Use full_text instead of abstract
        max_workers=4
    )
    
    # Connect to database
    db_manager = PostgreSQLManager(**db_config)
    db_manager.connect()
    
    # Create chunking pipeline
    pipeline = ChunkingPipeline(config, db_manager)
    
    # Process chunks
    chunks_file = "data/processed/arxiv_chunks.jsonl"
    pipeline.process_from_database(chunks_file, batch_size=1000, limit=limit)
    
    db_manager.close()
    
    print(f"✅ Chunking Complete!")
    print(f"   Processed papers: {pipeline.processed_docs}")
    print(f"   Total chunks: {pipeline.total_chunks}")
    print(f"   Chunks file: {chunks_file}")
    
    return pipeline.processed_docs, pipeline.total_chunks, chunks_file


def generate_embeddings(chunks_file: str, use_pinecone: bool = True, 
                       pinecone_api_key: str = None, pinecone_index: str = None):
    """Step 3: Generate embeddings and store in Pinecone + FAISS."""
    print("\n" + "="*60)
    print("🧠 STEP 3: Embedding Generation & Storage")
    print("="*60)
    
    # Embedding configuration
    config = EmbeddingConfig(
        model_name=Config.EMBEDDING_MODEL_NAME,
        batch_size=Config.EMBEDDING_BATCH_SIZE,
        max_workers=4,
        normalize_vectors=Config.EMBEDDING_NORMALIZE_VECTORS,
        # FAISS configuration
        use_faiss=True,
        faiss_index_type='IndexFlatIP',
        faiss_metadata_file=os.path.join(Config.PROCESSED_DATA_DIR, 'faiss_metadata.jsonl'),
        faiss_index_file=os.path.join(Config.PROCESSED_DATA_DIR, 'faiss_index.bin'),
        # Pinecone configuration
        use_pinecone=use_pinecone,
        pinecone_api_key=pinecone_api_key or Config.PINECONE_API_KEY,
        pinecone_index_name=pinecone_index or Config.PINECONE_INDEX_NAME,
        pinecone_environment=Config.PINECONE_ENVIRONMENT
    )
    
    # Create embedding pipeline
    pipeline = EmbeddingPipeline(config)
    
    embeddings_file = "data/processed/arxiv_embeddings.jsonl"
    
    if use_pinecone and config.pinecone_api_key:
        print("🌲 Hybrid Workflow: Pinecone Storage + FAISS Search")
        print("   Step 3a: Storing embeddings in Pinecone...")
        print("   Step 3b: Retrieving from Pinecone to create FAISS index...")
        pipeline.process_chunks_file_with_pinecone(chunks_file, embeddings_file, batch_size=1000)
    else:
        print("💾 Storing embeddings to file only...")
        pipeline.process_chunks_file(chunks_file, embeddings_file, batch_size=1000)
        
        # Create FAISS index only if not using Pinecone
        print("\n🔍 Creating FAISS Vector Index")
        print("-" * 30)
        pipeline.create_faiss_index(chunks_file, batch_size=1000)
    
    print(f"✅ Embedding Generation Complete!")
    print(f"   Processed chunks: {pipeline.processed_chunks}")
    print(f"   Total embeddings: {pipeline.total_embeddings}")
    print(f"   Vector dimension: {config.vector_dimension}")
    print(f"   FAISS index: {os.path.join(Config.PROCESSED_DATA_DIR, 'faiss_index.bin')}")
    print(f"   FAISS metadata: {os.path.join(Config.PROCESSED_DATA_DIR, 'faiss_metadata.jsonl')}")
    if use_pinecone and config.pinecone_api_key:
        print(f"   Pinecone index: {pinecone_index or Config.PINECONE_INDEX_NAME}")
        print(f"   Pinecone environment: {Config.PINECONE_ENVIRONMENT}")
    
    return pipeline.processed_chunks, pipeline.total_embeddings


def create_search_scripts():
    """Step 4: Create search scripts for FAISS and Pinecone."""
    print("\n" + "="*60)
    print("🔍 STEP 4: Creating Search Scripts")
    print("="*60)
    
    # FAISS search script
    faiss_search_script = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
\"\"\"
FAISS Search Script
==================

Search the local FAISS index for similar chunks.
\"\"\"

import sys
import argparse
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from data_processing.embedding_generation import EmbeddingPipeline, EmbeddingConfig
from config import Config

def search_faiss(query: str, n_results: int = 5):
    \"\"\"Search FAISS index.\"\"\"
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
        print(f"\\n{i}. Score: {result['score']:.4f}")
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
"""
    
    with open("scripts/search_faiss.py", "w") as f:
        f.write(faiss_search_script)
    
    print("✅ Search scripts created:")
    print("   - scripts/search_faiss.py")
    print("   - scripts/search_pinecone.py (already exists)")
    print("   - scripts/sync_pinecone_to_faiss.py (already exists)")


def main():
    """Main function for the complete pipeline."""
    parser = argparse.ArgumentParser(description='Complete RAG Pipeline for ArXiv PDFs')
    
    # Processing options
    parser.add_argument('--pdf-dir', default='data/pdfs', help='PDF directory')
    parser.add_argument('--limit', type=int, help='Limit number of PDFs to process')
    parser.add_argument('--clear-db', action='store_true', help='Clear database before processing')
    
    # Pinecone configuration
    parser.add_argument('--pinecone', action='store_true', help='Use Pinecone for storage')
    parser.add_argument('--pinecone-api-key', help='Pinecone API key')
    parser.add_argument('--pinecone-index', help='Pinecone index name')
    
    # Database configuration
    parser.add_argument('--db-host', default=Config.DB_HOST, help='PostgreSQL host')
    parser.add_argument('--db-port', type=int, default=Config.DB_PORT, help='PostgreSQL port')
    parser.add_argument('--db-name', default=Config.DB_NAME, help='PostgreSQL database name')
    parser.add_argument('--db-user', default=Config.DB_USER, help='PostgreSQL username')
    parser.add_argument('--db-password', default=Config.DB_PASSWORD, help='PostgreSQL password')
    
    args = parser.parse_args()
    
    # Validate PDF directory
    pdf_dir = Path(args.pdf_dir)
    if not pdf_dir.exists():
        print(f"❌ Error: PDF directory {pdf_dir} not found!")
        return
    
    # Count PDF files
    pdf_files = list(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ Error: No PDF files found in {pdf_dir}")
        return
    
    print(f"📁 Found {len(pdf_files)} PDF files in {pdf_dir}")
    
    # Database configuration
    db_config = {
        'host': args.db_host,
        'port': args.db_port,
        'database': args.db_name,
        'user': args.db_user,
        'password': args.db_password
    }
    
    # Clear database if requested
    if args.clear_db:
        print("\n🗑️  Clearing database...")
        # Import clear_database function directly
        sys.path.append(str(Path(__file__).parent))
        from clear_database import clear_database
        if not clear_database(db_config):
            print("❌ Failed to clear database. Aborting.")
            return
        print("✅ Database cleared successfully!")
    
    # Create output directory
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*60)
    print("🚀 COMPLETE RAG PIPELINE")
    print("="*60)
    if args.limit:
        print(f"Processing {args.limit} PDFs (limited)")
    else:
        print(f"Processing all {len(pdf_files)} PDFs")
    print(f"PDF Directory: {pdf_dir}")
    print(f"Database: {db_config['database']}")
    print()
    
    start_time = time.time()
    
    try:
        # Step 1: Process PDFs
        processed_pdfs = process_pdfs(str(pdf_dir), db_config, args.limit)
        
        if processed_pdfs == 0:
            print("❌ No PDFs were processed successfully. Aborting.")
            return
        
        # Step 2: Chunk papers
        chunked_papers, total_chunks, chunks_file = chunk_papers(db_config, args.limit)
        
        if total_chunks == 0:
            print("❌ No chunks were created. Aborting.")
            return
        
        # Step 3: Generate embeddings
        embedded_chunks, total_embeddings = generate_embeddings(
            chunks_file, 
            use_pinecone=args.pinecone,
            pinecone_api_key=args.pinecone_api_key,
            pinecone_index=args.pinecone_index
        )
        
        # Step 4: Create search scripts
        create_search_scripts()
        
        # Final summary
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "="*60)
        print("🎉 PIPELINE COMPLETE!")
        print("="*60)
        print(f"✅ PDFs processed: {processed_pdfs}")
        print(f"✅ Papers chunked: {chunked_papers}")
        print(f"✅ Total chunks: {total_chunks}")
        print(f"✅ Chunks embedded: {embedded_chunks}")
        print(f"✅ Total embeddings: {total_embeddings}")
        print(f"⏱️  Total time: {duration:.2f} seconds")
        print()
        print("🔍 You can now search using:")
        print("   python scripts/search_faiss.py --query 'your search query'")
        print("   python scripts/search_pinecone.py --query 'your search query'")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {str(e)}")
        print("Please check the error messages above.")


if __name__ == "__main__":
    main()
