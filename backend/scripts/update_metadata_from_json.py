#!/usr/bin/env python3
"""
Update database metadata from arxiv-metadata JSON file.
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

def get_database_paper_ids():
    """Get all paper IDs that exist in the database."""
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='Codemate',
        user='postgres',
        password='akash'
    )
    
    with conn.cursor() as cursor:
        cursor.execute("SELECT id FROM papers")
        paper_ids = {row[0] for row in cursor.fetchall()}
    
    conn.close()
    return paper_ids

def update_database_metadata():
    """Update database with correct metadata from JSON file."""
    try:
        # Connect to database
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='Codemate',
            user='postgres',
            password='akash'
        )
        
        # Get existing paper IDs from database
        logger.info("Loading existing paper IDs from database...")
        db_paper_ids = get_database_paper_ids()
        logger.info(f"Found {len(db_paper_ids)} papers in database")
        
        # Load JSON metadata
        json_file = Path(__file__).parent.parent / 'data' / 'arxiv-metadata-oai-snapshot.json'
        logger.info(f"Loading metadata from {json_file}")
        
        updated_count = 0
        not_found_count = 0
        error_count = 0
        json_paper_ids = set()
        
        with open(json_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                
                try:
                    # Parse JSON line
                    metadata = json.loads(line.strip())
                    paper_id = metadata.get('id')
                    
                    if not paper_id:
                        continue
                    
                    json_paper_ids.add(paper_id)
                    
                    # Only process papers that exist in our database
                    if paper_id not in db_paper_ids:
                        not_found_count += 1
                        if not_found_count % 100 == 0:
                            logger.info(f"Not in database: {not_found_count} papers...")
                        continue
                    
                    # Extract metadata
                    title = metadata.get('title', '').replace('\n', ' ').strip()
                    authors = metadata.get('authors', '').replace('\\', '').strip()  # Remove escape characters
                    abstract = metadata.get('abstract', '').replace('\n', ' ').strip()
                    categories = metadata.get('categories', '').strip()
                    
                    # Validate that we have meaningful data
                    if not authors or authors == "Unknown Authors" or len(authors) < 3:
                        logger.warning(f"Skipping {paper_id} - invalid authors: {authors}")
                        continue
                    
                    # Update database
                    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                        # Double-check paper exists and get current data
                        cursor.execute("SELECT id, title, authors FROM papers WHERE id = %s", (paper_id,))
                        current_paper = cursor.fetchone()
                        
                        if current_paper:
                            # Log what we're updating
                            logger.info(f"Updating {paper_id}:")
                            logger.info(f"  Old title: {current_paper['title'][:50]}...")
                            logger.info(f"  New title: {title[:50]}...")
                            logger.info(f"  Old authors: {current_paper['authors'][:50]}...")
                            logger.info(f"  New authors: {authors[:50]}...")
                            
                            # Update the paper
                            cursor.execute("""
                                UPDATE papers 
                                SET title = %s, authors = %s, abstract = %s, categories = %s
                                WHERE id = %s
                            """, (title, authors, abstract, categories, paper_id))
                            
                            updated_count += 1
                            if updated_count % 10 == 0:
                                logger.info(f"Updated {updated_count} papers...")
                        else:
                            logger.warning(f"Paper {paper_id} not found in database during update")
                
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error at line {line_num}: {e}")
                    error_count += 1
                    continue
                except Exception as e:
                    logger.error(f"Error processing line {line_num}: {e}")
                    error_count += 1
                    continue
        
        # Commit changes
        conn.commit()
        
        logger.info(f"Update completed!")
        logger.info(f"Updated papers: {updated_count}")
        logger.info(f"Not found in database: {not_found_count}")
        logger.info(f"Errors: {error_count}")
        logger.info(f"Total JSON papers processed: {len(json_paper_ids)}")
        
        # Verify some updates
        logger.info("Verifying updates...")
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id, title, authors FROM papers WHERE authors != 'Unknown Authors' AND authors NOT LIKE '%YSO Population%' LIMIT 5")
            papers = cursor.fetchall()
            for paper in papers:
                logger.info(f"ID: {paper['id']}, Authors: {paper['authors'][:50]}...")
        
        # Check overlap between JSON and database
        overlap = db_paper_ids.intersection(json_paper_ids)
        logger.info(f"Papers in both database and JSON: {len(overlap)}")
        logger.info(f"Papers only in database: {len(db_paper_ids - json_paper_ids)}")
        logger.info(f"Papers only in JSON: {len(json_paper_ids - db_paper_ids)}")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to update database: {e}")
        raise

if __name__ == "__main__":
    update_database_metadata()
