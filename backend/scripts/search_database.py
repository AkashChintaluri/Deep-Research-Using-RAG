#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Search Script
=====================

Search the PostgreSQL database for papers using full-text search.
"""

import sys
import argparse
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from services.data_ingestion_postgres import PostgreSQLManager
from core.config import Config

def search_database(query: str, n_results: int = 5):
    """Search the database using full-text search."""
    db_config = Config.get_database_config()
    db_manager = PostgreSQLManager(**db_config)
    
    try:
        db_manager.connect()
        
        # Full-text search query
        search_query = """
            SELECT id, title, authors, abstract, 
                   ts_rank(to_tsvector('english', title || ' ' || abstract || ' ' || full_text), 
                           plainto_tsquery('english', %s)) as rank
            FROM papers 
            WHERE to_tsvector('english', title || ' ' || abstract || ' ' || full_text) 
                  @@ plainto_tsquery('english', %s)
            ORDER BY rank DESC
            LIMIT %s
        """
        
        db_manager.cursor.execute(search_query, (query, query, n_results))
        results = db_manager.cursor.fetchall()
        
        print(f"Search Results for: '{query}'")
        print("=" * 60)
        print(f"Found {len(results)} results")
        print()
        
        for i, result in enumerate(results, 1):
            print(f"{i}. Paper ID: {result['id']}")
            print(f"   Title: {result['title']}")
            print(f"   Authors: {result['authors'][:100]}...")
            print(f"   Abstract: {result['abstract'][:200]}...")
            print(f"   Relevance Score: {result['rank']:.4f}")
            print("-" * 60)
        
        return results
        
    except Exception as e:
        print(f"Error searching database: {e}")
        return []
    finally:
        db_manager.close()

def search_by_category(category: str, n_results: int = 5):
    """Search papers by category."""
    db_config = Config.get_database_config()
    db_manager = PostgreSQLManager(**db_config)
    
    try:
        db_manager.connect()
        
        query = """
            SELECT id, title, authors, abstract, categories
            FROM papers 
            WHERE categories ILIKE %s
            ORDER BY id
            LIMIT %s
        """
        
        db_manager.cursor.execute(query, (f'%{category}%', n_results))
        results = db_manager.cursor.fetchall()
        
        print(f"Papers in category: '{category}'")
        print("=" * 60)
        print(f"Found {len(results)} results")
        print()
        
        for i, result in enumerate(results, 1):
            print(f"{i}. Paper ID: {result['id']}")
            print(f"   Title: {result['title']}")
            print(f"   Authors: {result['authors'][:100]}...")
            print(f"   Categories: {result['categories']}")
            print("-" * 60)
        
        return results
        
    except Exception as e:
        print(f"Error searching by category: {e}")
        return []
    finally:
        db_manager.close()

def get_database_stats():
    """Get database statistics."""
    db_config = Config.get_database_config()
    db_manager = PostgreSQLManager(**db_config)
    
    try:
        db_manager.connect()
        
        # Total papers
        db_manager.cursor.execute("SELECT COUNT(*) as total FROM papers")
        total_papers = db_manager.cursor.fetchone()['total']
        
        # Papers with full text
        db_manager.cursor.execute("SELECT COUNT(*) as total FROM papers WHERE full_text IS NOT NULL AND LENGTH(full_text) > 0")
        papers_with_text = db_manager.cursor.fetchone()['total']
        
        # Average text length
        db_manager.cursor.execute("SELECT AVG(LENGTH(full_text)) as avg_length FROM papers WHERE full_text IS NOT NULL")
        avg_length = db_manager.cursor.fetchone()['avg_length']
        
        # Top categories
        db_manager.cursor.execute("""
            SELECT categories, COUNT(*) as count 
            FROM papers 
            GROUP BY categories 
            ORDER BY count DESC 
            LIMIT 5
        """)
        top_categories = db_manager.cursor.fetchall()
        
        print("Database Statistics")
        print("=" * 40)
        print(f"Total papers: {total_papers}")
        print(f"Papers with full text: {papers_with_text}")
        print(f"Average text length: {avg_length:.0f} characters")
        print()
        print("Top categories:")
        for cat in top_categories:
            print(f"  {cat['categories']}: {cat['count']} papers")
        
    except Exception as e:
        print(f"Error getting statistics: {e}")
    finally:
        db_manager.close()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Search the ArXiv papers database')
    
    # Search options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--search', '-s', help='Search query for full-text search')
    group.add_argument('--category', '-c', help='Search by category')
    group.add_argument('--stats', action='store_true', help='Show database statistics')
    
    parser.add_argument('--n-results', '-n', type=int, default=5, help='Number of results to show')
    
    args = parser.parse_args()
    
    if args.stats:
        get_database_stats()
    elif args.search:
        search_database(args.search, args.n_results)
    elif args.category:
        search_by_category(args.category, args.n_results)

if __name__ == "__main__":
    main()
