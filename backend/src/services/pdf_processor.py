#!/usr/bin/env python3
"""
PDF Processing Pipeline for ArXiv Papers
========================================

This script processes PDF files from the astro_ph_pdfs directory and extracts:
- Full text content from PDFs
- Metadata (title, authors, abstract, etc.)
- Structured data for database storage

Key Features:
- PDF text extraction using PyPDF2/pdfplumber
- Metadata extraction and normalization
- Database storage with full-text search
- Batch processing for efficiency
- Error handling and logging
"""

import os
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import argparse
from tqdm import tqdm

# PDF processing libraries
try:
    import PyPDF2
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("Warning: PDF processing libraries not available. Install with: pip install PyPDF2 pdfplumber")

# Database imports
import psycopg2
import psycopg2.extras

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PDFTextExtractor:
    """Handles PDF text extraction using multiple methods."""
    
    def __init__(self):
        self.extraction_methods = ['pdfplumber', 'pypdf2']
    
    def extract_text_pdfplumber(self, pdf_path: str) -> str:
        """Extract text using pdfplumber (better for complex layouts)."""
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text.strip()
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed for {pdf_path}: {str(e)}")
            return ""
    
    def extract_text_pypdf2(self, pdf_path: str) -> str:
        """Extract text using PyPDF2 (fallback method)."""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text.strip()
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed for {pdf_path}: {str(e)}")
            return ""
    
    def extract_text(self, pdf_path: str) -> str:
        """Extract text using the best available method."""
        if not PDF_AVAILABLE:
            logger.error("PDF processing libraries not available")
            return ""
        
        # Try pdfplumber first (better quality)
        text = self.extract_text_pdfplumber(pdf_path)
        if text and len(text) > 100:  # Reasonable text length
            return text
        
        # Fallback to PyPDF2
        text = self.extract_text_pypdf2(pdf_path)
        if text and len(text) > 100:
            return text
        
        logger.warning(f"Could not extract meaningful text from {pdf_path}")
        return ""


class TextNormalizer:
    """Handles text normalization for PDF content."""
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text by cleaning and formatting."""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize line breaks
        text = re.sub(r'\s+', ' ', text)
        
        # Remove LaTeX commands and special characters
        text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text)  # LaTeX commands with braces
        text = re.sub(r'\\[a-zA-Z]+', '', text)  # Remaining LaTeX commands
        text = re.sub(r'[{}]', '', text)  # Remove braces
        text = re.sub(r'[\\]', '', text)  # Remove backslashes
        
        # Clean up mathematical symbols but keep basic punctuation
        text = re.sub(r'[^\w\s.,;:!?()-]', '', text)
        
        # Clean up multiple spaces and trim
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @staticmethod
    def extract_metadata_from_text(text: str, paper_id: str) -> Dict[str, Any]:
        """Extract metadata from PDF text content."""
        lines = text.split('\n')
        
        # Try to extract title (usually in first few lines)
        title = ""
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            line = line.strip()
            if len(line) > 20 and not line.startswith(('arXiv:', 'Abstract:', 'Keywords:')):
                title = line
                break
        
        # Try to extract abstract
        abstract = ""
        abstract_start = -1
        for i, line in enumerate(lines):
            if 'abstract' in line.lower() and len(line.strip()) < 50:
                abstract_start = i + 1
                break
        
        if abstract_start > 0:
            abstract_lines = []
            for i in range(abstract_start, min(abstract_start + 20, len(lines))):
                line = lines[i].strip()
                if line and not line.startswith(('Keywords:', 'Introduction', '1.', '2.')):
                    abstract_lines.append(line)
                elif line.startswith(('Keywords:', 'Introduction', '1.', '2.')):
                    break
            abstract = ' '.join(abstract_lines)
        
        # Try to extract authors (look for common patterns)
        authors = ""
        for i, line in enumerate(lines[:20]):  # Check first 20 lines
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['author', 'authors', 'by']):
                # Look at next few lines for author names
                for j in range(i+1, min(i+5, len(lines))):
                    author_line = lines[j].strip()
                    if author_line and len(author_line) > 5:
                        authors = author_line
                        break
                break
        
        return {
            'title': TextNormalizer.normalize_text(title),
            'abstract': TextNormalizer.normalize_text(abstract),
            'authors': TextNormalizer.normalize_text(authors)
        }


class PDFProcessor:
    """Main class for processing PDF files."""
    
    def __init__(self, pdf_directory: str, db_config: Dict[str, Any]):
        """
        Initialize the PDF processor.
        
        Args:
            pdf_directory: Directory containing PDF files
            db_config: Database configuration
        """
        self.pdf_directory = Path(pdf_directory)
        self.db_config = db_config
        self.text_extractor = PDFTextExtractor()
        self.normalizer = TextNormalizer()
        
        # Statistics
        self.processed_count = 0
        self.error_count = 0
        self.total_text_length = 0
        
        # Database connection
        self.connection = None
        self.cursor = None
    
    def connect_database(self):
        """Connect to PostgreSQL database."""
        try:
            self.connection = psycopg2.connect(**self.db_config)
            self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            logger.info(f"Connected to PostgreSQL database: {self.db_config['database']}")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            raise
    
    def create_tables(self):
        """Create tables for PDF data storage."""
        try:
            # Create papers table with enhanced schema for PDF content
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS papers (
                    id VARCHAR(50) PRIMARY KEY,
                    title TEXT,
                    authors TEXT,
                    abstract TEXT,
                    body TEXT,
                    full_text TEXT,
                    version VARCHAR(10) DEFAULT 'v1',
                    total_versions INTEGER DEFAULT 1,
                    first_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    update_date DATE DEFAULT CURRENT_DATE,
                    categories TEXT DEFAULT 'astro-ph',
                    doi VARCHAR(255),
                    journal_ref TEXT,
                    comments TEXT,
                    license TEXT,
                    submitter VARCHAR(255),
                    authors_parsed JSONB,
                    pdf_path TEXT,
                    text_length INTEGER,
                    word_count INTEGER,
                    processed_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            
            self.cursor.execute(create_table_sql)
            
            # Create indexes for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_papers_categories ON papers USING GIN (string_to_array(categories, ' '))",
                "CREATE INDEX IF NOT EXISTS idx_papers_update_date ON papers (update_date)",
                "CREATE INDEX IF NOT EXISTS idx_papers_text_length ON papers (text_length)",
                "CREATE INDEX IF NOT EXISTS idx_papers_word_count ON papers (word_count)",
                "CREATE INDEX IF NOT EXISTS idx_papers_processed_timestamp ON papers (processed_timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_papers_title_gin ON papers USING GIN (to_tsvector('english', title))",
                "CREATE INDEX IF NOT EXISTS idx_papers_abstract_gin ON papers USING GIN (to_tsvector('english', abstract))",
                "CREATE INDEX IF NOT EXISTS idx_papers_full_text_gin ON papers USING GIN (to_tsvector('english', full_text))",
                "CREATE INDEX IF NOT EXISTS idx_papers_body_gin ON papers USING GIN (to_tsvector('english', body))"
            ]
            
            for index_sql in indexes:
                self.cursor.execute(index_sql)
            
            self.connection.commit()
            logger.info("Database tables and indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise
    
    def process_pdf(self, pdf_path: Path) -> Optional[Dict[str, Any]]:
        """
        Process a single PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Processed paper data or None if failed
        """
        try:
            # Extract paper ID from filename
            paper_id = pdf_path.stem
            
            # Extract text from PDF
            logger.info(f"Processing PDF: {pdf_path.name}")
            full_text = self.text_extractor.extract_text(str(pdf_path))
            
            if not full_text:
                logger.warning(f"No text extracted from {pdf_path.name}")
                self.error_count += 1
                return None
            
            # Extract metadata from text
            metadata = self.normalizer.extract_metadata_from_text(full_text, paper_id)
            
            # Calculate text statistics
            text_length = len(full_text)
            word_count = len(full_text.split())
            
            # Create processed record
            processed_paper = {
                'id': paper_id,
                'title': metadata['title'] or f"Paper {paper_id}",
                'authors': metadata['authors'] or "Unknown Authors",
                'abstract': metadata['abstract'] or "",
                'body': metadata['abstract'] or full_text[:1000],  # Use abstract or first 1000 chars
                'full_text': self.normalizer.normalize_text(full_text),
                'version': 'v1',
                'total_versions': 1,
                'first_created': datetime.now(),
                'last_updated': datetime.now(),
                'update_date': datetime.now().date(),
                'categories': 'astro-ph',
                'doi': '',
                'journal_ref': '',
                'comments': '',
                'license': '',
                'submitter': '',
                'authors_parsed': json.dumps([]),
                'pdf_path': str(pdf_path),
                'text_length': text_length,
                'word_count': word_count,
                'processed_timestamp': datetime.now()
            }
            
            return processed_paper
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path.name}: {str(e)}")
            self.error_count += 1
            return None
    
    def insert_paper(self, paper_data: Dict[str, Any]):
        """Insert a single paper into the database."""
        try:
            insert_sql = """
                INSERT INTO papers (
                    id, title, authors, abstract, body, full_text, version, total_versions,
                    first_created, last_updated, update_date, categories, doi,
                    journal_ref, comments, license, submitter, authors_parsed, 
                    pdf_path, text_length, word_count, processed_timestamp
                ) VALUES (
                    %(id)s, %(title)s, %(authors)s, %(abstract)s, %(body)s, %(full_text)s, 
                    %(version)s, %(total_versions)s, %(first_created)s, %(last_updated)s, 
                    %(update_date)s, %(categories)s, %(doi)s, %(journal_ref)s, %(comments)s, 
                    %(license)s, %(submitter)s, %(authors_parsed)s::jsonb, %(pdf_path)s, 
                    %(text_length)s, %(word_count)s, %(processed_timestamp)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    authors = EXCLUDED.authors,
                    abstract = EXCLUDED.abstract,
                    body = EXCLUDED.body,
                    full_text = EXCLUDED.full_text,
                    version = EXCLUDED.version,
                    total_versions = EXCLUDED.total_versions,
                    first_created = EXCLUDED.first_created,
                    last_updated = EXCLUDED.last_updated,
                    update_date = EXCLUDED.update_date,
                    categories = EXCLUDED.categories,
                    doi = EXCLUDED.doi,
                    journal_ref = EXCLUDED.journal_ref,
                    comments = EXCLUDED.comments,
                    license = EXCLUDED.license,
                    submitter = EXCLUDED.submitter,
                    authors_parsed = EXCLUDED.authors_parsed::jsonb,
                    pdf_path = EXCLUDED.pdf_path,
                    text_length = EXCLUDED.text_length,
                    word_count = EXCLUDED.word_count,
                    processed_timestamp = EXCLUDED.processed_timestamp
            """
            
            self.cursor.execute(insert_sql, paper_data)
            self.connection.commit()
            
        except Exception as e:
            logger.error(f"Failed to insert paper {paper_data.get('id', 'unknown')}: {str(e)}")
            self.connection.rollback()
            raise
    
    def process_all_pdfs(self, limit: Optional[int] = None):
        """Process all PDF files in the directory."""
        if not PDF_AVAILABLE:
            logger.error("PDF processing libraries not available. Install with: pip install PyPDF2 pdfplumber")
            return
        
        # Connect to database
        self.connect_database()
        self.create_tables()
        
        # Get list of PDF files
        pdf_files = list(self.pdf_directory.glob("*.pdf"))
        if limit:
            pdf_files = pdf_files[:limit]
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        # Process each PDF
        with tqdm(total=len(pdf_files), desc="Processing PDFs") as pbar:
            for pdf_path in pdf_files:
                try:
                    # Process PDF
                    processed_paper = self.process_pdf(pdf_path)
                    
                    if processed_paper:
                        # Insert into database
                        self.insert_paper(processed_paper)
                        
                        # Update statistics
                        self.processed_count += 1
                        self.total_text_length += processed_paper['text_length']
                        
                        # Log progress
                        if self.processed_count % 10 == 0:
                            logger.info(f"Processed {self.processed_count} PDFs so far...")
                    
                    pbar.update(1)
                    
                except Exception as e:
                    logger.error(f"Unexpected error processing {pdf_path.name}: {str(e)}")
                    self.error_count += 1
                    pbar.update(1)
                    continue
        
        # Final statistics
        logger.info(f"PDF processing completed!")
        logger.info(f"Total processed: {self.processed_count}")
        logger.info(f"Errors: {self.error_count}")
        logger.info(f"Total text length: {self.total_text_length:,} characters")
        logger.info(f"Average text length: {self.total_text_length // max(self.processed_count, 1):,} characters per paper")
        
        # Close database connection
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("Database connection closed")


def main():
    """Main function to run the PDF processing pipeline."""
    parser = argparse.ArgumentParser(description='Process PDF files for data ingestion')
    parser.add_argument('--pdf-dir', '-d', default='astro_ph_pdfs', 
                       help='Directory containing PDF files')
    parser.add_argument('--limit', type=int, help='Limit number of PDFs to process')
    parser.add_argument('--db-host', default='localhost', help='PostgreSQL host')
    parser.add_argument('--db-port', type=int, default=5432, help='PostgreSQL port')
    parser.add_argument('--db-name', default='Codemate', help='PostgreSQL database name')
    parser.add_argument('--db-user', default='postgres', help='PostgreSQL username')
    parser.add_argument('--db-password', default='akash', help='PostgreSQL password')
    
    args = parser.parse_args()
    
    # Validate PDF directory
    pdf_dir = Path(args.pdf_dir)
    if not pdf_dir.exists():
        logger.error(f"PDF directory {pdf_dir} does not exist!")
        return
    
    # Database configuration
    db_config = {
        'host': args.db_host,
        'port': args.db_port,
        'database': args.db_name,
        'user': args.db_user,
        'password': args.db_password
    }
    
    # Create processor and run
    processor = PDFProcessor(str(pdf_dir), db_config)
    processor.process_all_pdfs(args.limit)


if __name__ == "__main__":
    main()
