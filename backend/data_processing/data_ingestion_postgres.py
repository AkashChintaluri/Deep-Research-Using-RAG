#!/usr/bin/env python3
"""
ArXiv Data Ingestion Pipeline with PostgreSQL
============================================

This script processes the ArXiv metadata snapshot and extracts key fields
for further analysis. It handles text normalization and stores data in
both JSONL and PostgreSQL formats.

Key Features:
- Parses JSON Lines format from ArXiv metadata
- Extracts: id, title, authors, abstract, body, version, update_date
- Normalizes text (removes extra whitespace, special characters)
- Stores in both JSONL and PostgreSQL formats
- Handles large files efficiently with streaming
- Configurable PostgreSQL connection settings
"""

import json
import psycopg2
import psycopg2.extras
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse
from tqdm import tqdm
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_ingestion_postgres.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TextNormalizer:
    """Handles text normalization for ArXiv data."""
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize text by removing extra whitespace and special characters.
        
        Args:
            text: Input text to normalize
            
        Returns:
            Normalized text
        """
        if not text:
            return ""
        
        # Remove extra whitespace and normalize line breaks
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special LaTeX characters and commands
        text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text)  # Remove LaTeX commands with braces
        text = re.sub(r'\\[a-zA-Z]+', '', text)  # Remove remaining LaTeX commands
        text = re.sub(r'[{}]', '', text)  # Remove braces
        text = re.sub(r'[\\]', '', text)  # Remove backslashes
        
        # Remove mathematical symbols and special characters
        text = re.sub(r'[^\w\s.,;:!?-]', '', text)
        
        # Clean up multiple spaces and trim
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @staticmethod
    def extract_version_info(versions: List[Dict]) -> Dict[str, Any]:
        """
        Extract version information from the versions array.
        
        Args:
            versions: List of version dictionaries
            
        Returns:
            Dictionary with version information
        """
        if not versions:
            return {"latest_version": "v1", "total_versions": 0, "first_created": None, "last_updated": None}
        
        # Sort by version number
        sorted_versions = sorted(versions, key=lambda x: x.get('version', 'v1'))
        
        return {
            "latest_version": sorted_versions[-1].get('version', 'v1'),
            "total_versions": len(versions),
            "first_created": sorted_versions[0].get('created'),
            "last_updated": sorted_versions[-1].get('created')
        }


class PostgreSQLManager:
    """Handles PostgreSQL database operations."""
    
    def __init__(self, host: str = "localhost", port: int = 5432, 
                 database: str = "arxiv", user: str = "postgres", 
                 password: str = None):
        """
        Initialize PostgreSQL connection.
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Username
            password: Password (if None, will try environment variable)
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password or os.getenv('POSTGRES_PASSWORD', 'postgres')
        
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Establish connection to PostgreSQL database."""
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            logger.info(f"Connected to PostgreSQL database: {self.database}")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            raise
    
    def create_tables(self):
        """Create tables and indexes for ArXiv data."""
        try:
            # Create papers table
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS papers (
                    id VARCHAR(50) PRIMARY KEY,
                    title TEXT,
                    authors TEXT,
                    abstract TEXT,
                    body TEXT,
                    version VARCHAR(10),
                    total_versions INTEGER,
                    first_created TIMESTAMP,
                    last_updated TIMESTAMP,
                    update_date DATE,
                    categories TEXT,
                    doi VARCHAR(255),
                    journal_ref TEXT,
                    comments TEXT,
                    license TEXT,
                    submitter VARCHAR(255),
                    authors_parsed JSONB,
                    processed_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            
            self.cursor.execute(create_table_sql)
            
            # Create indexes for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_papers_categories ON papers USING GIN (string_to_array(categories, ' '))",
                "CREATE INDEX IF NOT EXISTS idx_papers_update_date ON papers (update_date)",
                "CREATE INDEX IF NOT EXISTS idx_papers_version ON papers (version)",
                "CREATE INDEX IF NOT EXISTS idx_papers_total_versions ON papers (total_versions)",
                "CREATE INDEX IF NOT EXISTS idx_papers_processed_timestamp ON papers (processed_timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_papers_title_gin ON papers USING GIN (to_tsvector('english', title))",
                "CREATE INDEX IF NOT EXISTS idx_papers_abstract_gin ON papers USING GIN (to_tsvector('english', abstract))"
            ]
            
            for index_sql in indexes:
                self.cursor.execute(index_sql)
            
            self.connection.commit()
            logger.info("Database tables and indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise
    
    def insert_papers_batch(self, papers: List[Dict]):
        """Insert a batch of papers into the database."""
        try:
            insert_sql = """
                INSERT INTO papers (
                    id, title, authors, abstract, body, version, total_versions,
                    first_created, last_updated, update_date, categories, doi,
                    journal_ref, comments, license, submitter, authors_parsed, processed_timestamp
                ) VALUES (
                    %(id)s, %(title)s, %(authors)s, %(abstract)s, %(body)s, %(version)s, %(total_versions)s,
                    %(first_created)s, %(last_updated)s, %(update_date)s, %(categories)s, %(doi)s,
                    %(journal_ref)s, %(comments)s, %(license)s, %(submitter)s, %(authors_parsed)s::jsonb, %(processed_timestamp)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    authors = EXCLUDED.authors,
                    abstract = EXCLUDED.abstract,
                    body = EXCLUDED.body,
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
                    processed_timestamp = EXCLUDED.processed_timestamp
            """
            
            self.cursor.executemany(insert_sql, papers)
            self.connection.commit()
            
        except Exception as e:
            logger.error(f"Failed to insert papers batch: {str(e)}")
            self.connection.rollback()
            raise
    
    def get_statistics(self):
        """Get processing statistics from the database."""
        try:
            stats = {}
            
            # Total papers
            self.cursor.execute("SELECT COUNT(*) as total FROM papers")
            stats['total_papers'] = self.cursor.fetchone()['total']
            
            # Papers by category
            self.cursor.execute("""
                SELECT categories, COUNT(*) as count 
                FROM papers 
                GROUP BY categories 
                ORDER BY count DESC 
                LIMIT 10
            """)
            stats['top_categories'] = self.cursor.fetchall()
            
            # Papers by version count
            self.cursor.execute("""
                SELECT total_versions, COUNT(*) as count 
                FROM papers 
                GROUP BY total_versions 
                ORDER BY total_versions
            """)
            stats['version_distribution'] = self.cursor.fetchall()
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {str(e)}")
            return {}
    
    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("PostgreSQL connection closed")


class ArxivDataProcessor:
    """Main class for processing ArXiv metadata with PostgreSQL."""
    
    def __init__(self, input_file: str, output_dir: str = "processed_data",
                 db_config: Dict[str, Any] = None):
        """
        Initialize the processor.
        
        Args:
            input_file: Path to the input JSON file
            output_dir: Directory to store processed data
            db_config: PostgreSQL connection configuration
        """
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.normalizer = TextNormalizer()
        
        # Initialize PostgreSQL manager
        db_config = db_config or {}
        self.db_manager = PostgreSQLManager(**db_config)
        
        # Initialize counters
        self.processed_count = 0
        self.error_count = 0
        self.skipped_count = 0
        
    def process_paper(self, paper_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single paper record.
        
        Args:
            paper_data: Raw paper data from JSON
            
        Returns:
            Processed paper data or None if skipped
        """
        try:
            # Extract basic fields
            paper_id = paper_data.get('id', '')
            if not paper_id:
                self.skipped_count += 1
                return None
            
            # Extract and normalize title
            title = self.normalizer.normalize_text(paper_data.get('title', ''))
            
            # Extract and normalize authors
            authors_raw = paper_data.get('authors', '')
            authors = self.normalizer.normalize_text(authors_raw)
            
            # Extract and normalize abstract
            abstract = self.normalizer.normalize_text(paper_data.get('abstract', ''))
            
            # For ArXiv, the "body" is typically the abstract since full text isn't available
            body = abstract  # Using abstract as body for now
            
            # Extract version information
            versions = paper_data.get('versions', [])
            version_info = self.normalizer.extract_version_info(versions)
            
            # Extract update date
            update_date = paper_data.get('update_date', '')
            
            # Parse dates for PostgreSQL
            first_created = None
            last_updated = None
            if version_info['first_created']:
                try:
                    first_created = datetime.strptime(version_info['first_created'], '%a, %d %b %Y %H:%M:%S %Z')
                except:
                    pass
            
            if version_info['last_updated']:
                try:
                    last_updated = datetime.strptime(version_info['last_updated'], '%a, %d %b %Y %H:%M:%S %Z')
                except:
                    pass
            
            # Parse update_date
            parsed_update_date = None
            if update_date:
                try:
                    parsed_update_date = datetime.strptime(update_date, '%Y-%m-%d').date()
                except:
                    pass
            
            # Create processed record
            processed_paper = {
                'id': paper_id,
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'body': body,
                'version': version_info['latest_version'],
                'total_versions': version_info['total_versions'],
                'first_created': first_created,
                'last_updated': last_updated,
                'update_date': parsed_update_date,
                'categories': paper_data.get('categories', ''),
                'doi': paper_data.get('doi', ''),
                'journal_ref': paper_data.get('journal-ref', ''),
                'comments': self.normalizer.normalize_text(paper_data.get('comments', '')),
                'license': paper_data.get('license', ''),
                'submitter': paper_data.get('submitter', ''),
                'authors_parsed': json.dumps(paper_data.get('authors_parsed', [])),
                'processed_timestamp': datetime.now()
            }
            
            return processed_paper
            
        except Exception as e:
            logger.error(f"Error processing paper {paper_data.get('id', 'unknown')}: {str(e)}")
            self.error_count += 1
            return None
    
    def process_file_streaming(self, batch_size: int = 1000) -> None:
        """
        Process the input file in streaming mode to handle large files.
        
        Args:
            batch_size: Number of records to process in each batch
        """
        logger.info(f"Starting to process {self.input_file}")
        
        # Connect to PostgreSQL
        self.db_manager.connect()
        self.db_manager.create_tables()
        
        # Initialize output files
        jsonl_output = self.output_dir / "arxiv_processed.jsonl"
        
        batch = []
        
        with open(self.input_file, 'r', encoding='utf-8') as f:
            # Get total line count for progress bar
            total_lines = sum(1 for _ in f)
            f.seek(0)
            
            with tqdm(total=total_lines, desc="Processing papers") as pbar:
                for line_num, line in enumerate(f, 1):
                    try:
                        # Parse JSON line
                        paper_data = json.loads(line.strip())
                        
                        # Process paper
                        processed_paper = self.process_paper(paper_data)
                        
                        if processed_paper:
                            batch.append(processed_paper)
                            self.processed_count += 1
                            
                            # Write to JSONL
                            with open(jsonl_output, 'a', encoding='utf-8') as jsonl_file:
                                jsonl_file.write(json.dumps(processed_paper, default=str, ensure_ascii=False) + '\n')
                        
                        # Process batch when it reaches batch_size
                        if len(batch) >= batch_size:
                            self.db_manager.insert_papers_batch(batch)
                            batch = []
                        
                        pbar.update(1)
                        
                        # Log progress every 10000 records
                        if self.processed_count % 10000 == 0:
                            logger.info(f"Processed {self.processed_count} papers so far...")
                    
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error at line {line_num}: {str(e)}")
                        self.error_count += 1
                        continue
                    except Exception as e:
                        logger.error(f"Unexpected error at line {line_num}: {str(e)}")
                        self.error_count += 1
                        continue
                
                # Process remaining batch
                if batch:
                    self.db_manager.insert_papers_batch(batch)
        
        # Get final statistics
        stats = self.db_manager.get_statistics()
        
        # Final statistics
        logger.info(f"Processing completed!")
        logger.info(f"Total processed: {self.processed_count}")
        logger.info(f"Errors: {self.error_count}")
        logger.info(f"Skipped: {self.skipped_count}")
        logger.info(f"Database total papers: {stats.get('total_papers', 0)}")
        logger.info(f"Output files:")
        logger.info(f"  JSONL: {jsonl_output}")
        logger.info(f"  PostgreSQL: {self.db_manager.database}")
        
        # Show top categories
        if stats.get('top_categories'):
            logger.info("Top categories:")
            for cat in stats['top_categories'][:5]:
                logger.info(f"  {cat['categories']}: {cat['count']} papers")
        
        # Close database connection
        self.db_manager.close()


def main():
    """Main function to run the data ingestion pipeline."""
    parser = argparse.ArgumentParser(description='Process ArXiv metadata for data ingestion with PostgreSQL')
    parser.add_argument('--input', '-i', required=True, help='Path to input JSON file')
    parser.add_argument('--output', '-o', default='processed_data', help='Output directory')
    parser.add_argument('--batch-size', '-b', type=int, default=1000, help='Batch size for processing')
    
    # PostgreSQL connection arguments
    parser.add_argument('--db-host', default='localhost', help='PostgreSQL host')
    parser.add_argument('--db-port', type=int, default=5432, help='PostgreSQL port')
    parser.add_argument('--db-name', default='arxiv', help='PostgreSQL database name')
    parser.add_argument('--db-user', default='postgres', help='PostgreSQL username')
    parser.add_argument('--db-password', help='PostgreSQL password (or set POSTGRES_PASSWORD env var)')
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file {input_path} does not exist!")
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
    processor = ArxivDataProcessor(args.input, args.output, db_config)
    processor.process_file_streaming(args.batch_size)


if __name__ == "__main__":
    main()
