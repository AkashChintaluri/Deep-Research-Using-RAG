#!/usr/bin/env python3
"""
Verify JSON mapping to database papers.
"""

import json
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_json_mapping():
    """Verify the mapping between JSON metadata and database papers."""
    try:
        # Connect to database
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='Codemate',
            user='postgres',
            password='akash'
        )
        
        # Get database paper IDs
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM papers")
            db_paper_ids = {row[0] for row in cursor.fetchall()}
        
        logger.info(f"Found {len(db_paper_ids)} papers in database")
        
        # Load JSON metadata
        json_file = Path(__file__).parent.parent / 'data' / 'arxiv-metadata-oai-snapshot.json'
        logger.info(f"Loading metadata from {json_file}")
        
        json_paper_ids = set()
        sample_metadata = []
        
        with open(json_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                
                try:
                    metadata = json.loads(line.strip())
                    paper_id = metadata.get('id')
                    
                    if paper_id:
                        json_paper_ids.add(paper_id)
                        
                        # Collect sample metadata for verification
                        if len(sample_metadata) < 10 and paper_id in db_paper_ids:
                            sample_metadata.append({
                                'id': paper_id,
                                'title': metadata.get('title', ''),
                                'authors': metadata.get('authors', ''),
                                'abstract': metadata.get('abstract', '')[:100] + '...' if metadata.get('abstract') else ''
                            })
                
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error at line {line_num}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing line {line_num}: {e}")
                    continue
        
        logger.info(f"Found {len(json_paper_ids)} papers in JSON file")
        
        # Check overlap
        overlap = db_paper_ids.intersection(json_paper_ids)
        logger.info(f"Papers in both database and JSON: {len(overlap)}")
        logger.info(f"Papers only in database: {len(db_paper_ids - json_paper_ids)}")
        logger.info(f"Papers only in JSON: {len(json_paper_ids - db_paper_ids)}")
        
        # Show sample metadata
        logger.info("\nSample metadata from JSON:")
        for i, meta in enumerate(sample_metadata, 1):
            logger.info(f"{i}. ID: {meta['id']}")
            logger.info(f"   Title: {meta['title'][:60]}...")
            logger.info(f"   Authors: {meta['authors'][:60]}...")
            logger.info(f"   Abstract: {meta['abstract'][:60]}...")
            logger.info("")
        
        # Check current database state for these papers
        logger.info("Current database state for sample papers:")
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            for meta in sample_metadata[:3]:
                cursor.execute("SELECT id, title, authors FROM papers WHERE id = %s", (meta['id'],))
                paper = cursor.fetchone()
                if paper:
                    logger.info(f"ID: {paper['id']}")
                    logger.info(f"  Current title: {paper['title'][:60]}...")
                    logger.info(f"  Current authors: {paper['authors'][:60]}...")
                    logger.info(f"  JSON authors: {meta['authors'][:60]}...")
                    logger.info("")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to verify mapping: {e}")
        raise

if __name__ == "__main__":
    verify_json_mapping()
