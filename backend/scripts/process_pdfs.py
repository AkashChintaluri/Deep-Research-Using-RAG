#!/usr/bin/env python3
"""
PDF Processing Script for ArXiv Papers
=====================================

This script processes PDF files from the astro_ph_pdfs directory and stores
the extracted content in the PostgreSQL database.

Usage:
    # Process all PDFs
    python scripts/process_pdfs.py
    
    # Process first 10 PDFs (for testing)
    python scripts/process_pdfs.py --limit 10
    
    # Clear database and process all PDFs
    python scripts/process_pdfs.py --clear-db
"""

import sys
import os
import argparse
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from services.pdf_processor import PDFProcessor
from services.data_ingestion_postgres import PostgreSQLManager
from core.config import Config


def clear_database(db_config):
    """Clear all data from the database."""
    print("⚠️  WARNING: This will delete ALL data in the database!")
    print(f"Database: {db_config['database']}")
    print(f"Host: {db_config['host']}:{db_config['port']}")
    print()
    
    # Ask for confirmation
    confirm = input("Are you sure you want to delete ALL data? Type 'YES' to confirm: ")
    if confirm != 'YES':
        print("Operation cancelled.")
        return False
    
    print("Connecting to database...")
    db_manager = PostgreSQLManager(**db_config)
    
    try:
        db_manager.connect()
        print("Connected successfully!")
        
        # Get table information before clearing
        db_manager.cursor.execute("""
            SELECT table_name, 
                   (xpath('/row/cnt/text()', xml_count))[1]::text::int as row_count
            FROM (
                SELECT table_name, 
                       query_to_xml(format('select count(*) as cnt from %I.%I', 
                                          table_schema, table_name), false, true, '') as xml_count
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            ) t
            ORDER BY table_name;
        """)
        
        tables_info = db_manager.cursor.fetchall()
        
        if tables_info:
            print("\nCurrent database contents:")
            for table in tables_info:
                print(f"  {table['table_name']}: {table['row_count']} rows")
        else:
            print("No tables found in the database.")
        
        print("\nClearing database...")
        
        # Drop all tables (this will clear everything)
        db_manager.cursor.execute("""
            DO $$ 
            DECLARE 
                r RECORD;
            BEGIN
                -- Drop all tables in the public schema
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') 
                LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;
        """)
        
        db_manager.connection.commit()
        print("✅ Database cleared successfully!")
        
        # Verify tables are gone
        db_manager.cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """)
        
        remaining_tables = db_manager.cursor.fetchall()
        
        if remaining_tables:
            print(f"⚠️  Warning: {len(remaining_tables)} tables still exist:")
            for table in remaining_tables:
                print(f"  - {table['table_name']}")
        else:
            print("✅ All tables successfully removed.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error clearing database: {str(e)}")
        return False
    
    finally:
        db_manager.close()
        print("Database connection closed.")


def check_pdf_requirements():
    """Check if PDF processing requirements are installed."""
    try:
        import PyPDF2
        import pdfplumber
        print("✅ PDF processing libraries are available")
        return True
    except ImportError as e:
        print("❌ PDF processing libraries not available")
        print("Please install them with:")
        print("  pip install PyPDF2 pdfplumber")
        print(f"Error: {e}")
        return False


def main():
    """Main function for PDF processing."""
    parser = argparse.ArgumentParser(description='Process PDF files for data ingestion')
    
    # Actions
    parser.add_argument('--clear-db', action='store_true', help='Clear database before processing')
    parser.add_argument('--limit', type=int, help='Limit number of PDFs to process (for testing)')
    
    # PDF directory
    parser.add_argument('--pdf-dir', '-d', default='astro_ph_pdfs', 
                       help='Directory containing PDF files')
    
    # Database configuration (defaults from config.py)
    parser.add_argument('--db-host', default=Config.DB_HOST, help='PostgreSQL host')
    parser.add_argument('--db-port', type=int, default=Config.DB_PORT, help='PostgreSQL port')
    parser.add_argument('--db-name', default=Config.DB_NAME, help='PostgreSQL database name')
    parser.add_argument('--db-user', default=Config.DB_USER, help='PostgreSQL username')
    parser.add_argument('--db-password', default=Config.DB_PASSWORD, help='PostgreSQL password')
    
    args = parser.parse_args()
    
    # Check PDF processing requirements
    if not check_pdf_requirements():
        return
    
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
        if not clear_database(db_config):
            print("❌ Failed to clear database. Aborting.")
            return
        print("✅ Database cleared successfully!")
        print()
    
    print("=" * 60)
    print("Codemate PDF Processing Pipeline")
    print("=" * 60)
    if args.limit:
        print(f"Processing {args.limit} PDFs (limited)")
    else:
        print(f"Processing all {len(pdf_files)} PDFs")
    print(f"PDF Directory: {pdf_dir}")
    print(f"Database: {db_config['database']}")
    print()
    
    # Create processor and run
    try:
        processor = PDFProcessor(str(pdf_dir), db_config)
        processor.process_all_pdfs(args.limit)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Processing Summary")
        print("=" * 60)
        print(f"✅ PDFs processed: {processor.processed_count}")
        print(f"❌ Errors: {processor.error_count}")
        print(f"📄 Total text length: {processor.total_text_length:,} characters")
        if processor.processed_count > 0:
            print(f"📊 Average text length: {processor.total_text_length // processor.processed_count:,} characters per paper")
        print("=" * 60)
        
        if processor.processed_count > 0:
            print("\n🎉 PDF processing completed successfully!")
            print("You can now:")
            print("  1. Query the database for full-text search")
            print("  2. Run document chunking: python scripts/process_data.py --chunk")
            print("  3. Generate embeddings: python scripts/process_data.py --embed")
        else:
            print("\n❌ No PDFs were processed successfully.")
            print("Please check the error messages above.")
            
    except Exception as e:
        print(f"\n❌ Error during processing: {str(e)}")
        print("Please check the error messages above.")


if __name__ == "__main__":
    main()
