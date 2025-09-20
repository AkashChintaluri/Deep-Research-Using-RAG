#!/usr/bin/env python3
"""
PostgreSQL Query Examples for ArXiv Data
=======================================

This script demonstrates various queries you can run on the processed ArXiv data
stored in PostgreSQL.
"""

import psycopg2
import psycopg2.extras
from collections import Counter
import json

def connect_to_database():
    """Connect to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='Codemate',
            user='postgres',
            password='akash'
        )
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return conn, cursor
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return None, None

def basic_statistics(cursor):
    """Show basic statistics about the data."""
    print("📊 BASIC STATISTICS")
    print("=" * 50)
    
    # Total papers
    cursor.execute("SELECT COUNT(*) as total FROM papers")
    total = cursor.fetchone()['total']
    print(f"Total papers: {total:,}")
    
    # Papers by category
    cursor.execute("""
        SELECT categories, COUNT(*) as count 
        FROM papers 
        WHERE categories IS NOT NULL AND categories != ''
        GROUP BY categories 
        ORDER BY count DESC 
        LIMIT 10
    """)
    
    print("\nTop Categories:")
    for row in cursor.fetchall():
        print(f"  {row['categories']}: {row['count']} papers")
    
    # Version distribution
    cursor.execute("""
        SELECT total_versions, COUNT(*) as count 
        FROM papers 
        GROUP BY total_versions 
        ORDER BY total_versions
    """)
    
    print("\nVersion Distribution:")
    for row in cursor.fetchall():
        print(f"  {row['total_versions']} versions: {row['count']} papers")

def search_papers(cursor, search_term):
    """Search papers by title or abstract."""
    print(f"\n🔍 SEARCH RESULTS for '{search_term}'")
    print("=" * 50)
    
    cursor.execute("""
        SELECT id, title, authors, categories, version, total_versions
        FROM papers 
        WHERE to_tsvector('english', title || ' ' || abstract) @@ plainto_tsquery('english', %s)
        ORDER BY ts_rank(to_tsvector('english', title || ' ' || abstract), plainto_tsquery('english', %s)) DESC
        LIMIT 10
    """, (search_term, search_term))
    
    results = cursor.fetchall()
    if results:
        for i, paper in enumerate(results, 1):
            print(f"{i}. {paper['title'][:80]}...")
            print(f"   Authors: {paper['authors']}")
            print(f"   Categories: {paper['categories']}")
            print(f"   Version: {paper['version']} (Total: {paper['total_versions']})")
            print()
    else:
        print("No results found.")

def category_analysis(cursor):
    """Analyze papers by category."""
    print("\n📈 CATEGORY ANALYSIS")
    print("=" * 50)
    
    # Most active categories
    cursor.execute("""
        SELECT 
            unnest(string_to_array(categories, ' ')) as category,
            COUNT(*) as count
        FROM papers 
        WHERE categories IS NOT NULL AND categories != ''
        GROUP BY unnest(string_to_array(categories, ' '))
        ORDER BY count DESC
        LIMIT 15
    """)
    
    print("Most Active Categories:")
    for row in cursor.fetchall():
        print(f"  {row['category']}: {row['count']} papers")
    
    # Papers with multiple categories
    cursor.execute("""
        SELECT categories, COUNT(*) as count
        FROM papers 
        WHERE categories IS NOT NULL AND categories != ''
        AND array_length(string_to_array(categories, ' '), 1) > 1
        GROUP BY categories
        ORDER BY count DESC
        LIMIT 10
    """)
    
    print("\nMulti-category Papers:")
    for row in cursor.fetchall():
        print(f"  {row['categories']}: {row['count']} papers")

def version_analysis(cursor):
    """Analyze paper versions."""
    print("\n🔄 VERSION ANALYSIS")
    print("=" * 50)
    
    # Papers with most versions
    cursor.execute("""
        SELECT id, title, total_versions, first_created, last_updated
        FROM papers 
        WHERE total_versions > 1
        ORDER BY total_versions DESC, last_updated DESC
        LIMIT 10
    """)
    
    print("Papers with Most Versions:")
    for row in cursor.fetchall():
        print(f"  {row['id']}: {row['total_versions']} versions")
        print(f"    {row['title'][:60]}...")
        print(f"    First: {row['first_created']}, Last: {row['last_updated']}")
        print()
    
    # Version distribution over time
    cursor.execute("""
        SELECT 
            DATE_TRUNC('year', first_created) as year,
            AVG(total_versions) as avg_versions,
            COUNT(*) as paper_count
        FROM papers 
        WHERE first_created IS NOT NULL
        GROUP BY DATE_TRUNC('year', first_created)
        ORDER BY year
        LIMIT 10
    """)
    
    print("Average Versions by Year:")
    for row in cursor.fetchall():
        if row['year']:
            print(f"  {row['year'].year}: {row['avg_versions']:.2f} avg versions ({row['paper_count']} papers)")

def author_analysis(cursor):
    """Analyze authors."""
    print("\n👥 AUTHOR ANALYSIS")
    print("=" * 50)
    
    # Most prolific authors
    cursor.execute("""
        SELECT 
            unnest(string_to_array(authors, ',')) as author,
            COUNT(*) as paper_count
        FROM papers 
        WHERE authors IS NOT NULL AND authors != ''
        GROUP BY unnest(string_to_array(authors, ','))
        ORDER BY paper_count DESC
        LIMIT 10
    """)
    
    print("Most Prolific Authors:")
    for row in cursor.fetchall():
        author = row['author'].strip()
        if author and len(author) > 3:  # Filter out very short names
            print(f"  {author}: {row['paper_count']} papers")
    
    # Single author papers
    cursor.execute("""
        SELECT COUNT(*) as single_author_count
        FROM papers 
        WHERE authors IS NOT NULL AND authors != ''
        AND array_length(string_to_array(authors, ','), 1) = 1
    """)
    
    single_author = cursor.fetchone()['single_author_count']
    print(f"\nSingle Author Papers: {single_author}")

def recent_papers(cursor):
    """Show recent papers."""
    print("\n🕒 RECENT PAPERS")
    print("=" * 50)
    
    cursor.execute("""
        SELECT id, title, authors, categories, processed_timestamp
        FROM papers 
        ORDER BY processed_timestamp DESC
        LIMIT 5
    """)
    
    print("Most Recently Processed:")
    for row in cursor.fetchall():
        print(f"  {row['id']}: {row['title'][:60]}...")
        print(f"    Authors: {row['authors']}")
        print(f"    Processed: {row['processed_timestamp']}")
        print()

def main():
    """Main function to run all queries."""
    print("🔬 ArXiv Data Analysis with PostgreSQL")
    print("=" * 60)
    
    conn, cursor = connect_to_database()
    if not conn:
        return
    
    try:
        basic_statistics(cursor)
        category_analysis(cursor)
        version_analysis(cursor)
        author_analysis(cursor)
        recent_papers(cursor)
        
        # Interactive search
        print("\n🔍 INTERACTIVE SEARCH")
        print("=" * 50)
        search_terms = ["machine learning", "quantum", "neural network", "deep learning"]
        
        for term in search_terms:
            search_papers(cursor, term)
    
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
    
    finally:
        cursor.close()
        conn.close()
        print("\n✅ Analysis complete!")

if __name__ == "__main__":
    main()
