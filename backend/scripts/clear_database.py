#!/usr/bin/env python3
"""
Database Clear Script
====================

This script clears all data from the PostgreSQL database.
Use this when you want to start fresh with data ingestion.

⚠️ WARNING: This will delete ALL data in the database!
"""

import sys
import os
import argparse
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

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

def main():
    """Main function for clearing the database."""
    parser = argparse.ArgumentParser(description='Clear all data from the PostgreSQL database')
    
    # Database configuration
    parser.add_argument('--db-host', default=Config.DB_HOST, help='PostgreSQL host')
    parser.add_argument('--db-port', type=int, default=Config.DB_PORT, help='PostgreSQL port')
    parser.add_argument('--db-name', default=Config.DB_NAME, help='PostgreSQL database name')
    parser.add_argument('--db-user', default=Config.DB_USER, help='PostgreSQL username')
    parser.add_argument('--db-password', default=Config.DB_PASSWORD, help='PostgreSQL password')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompt (dangerous!)')
    
    args = parser.parse_args()
    
    # Database configuration
    db_config = {
        'host': args.db_host,
        'port': args.db_port,
        'database': args.db_name,
        'user': args.db_user,
        'password': args.db_password
    }
    
    print("=" * 60)
    print("Codemate Database Clear Script")
    print("=" * 60)
    print(f"Database: {db_config['database']}")
    print(f"Host: {db_config['host']}:{db_config['port']}")
    print(f"User: {db_config['user']}")
    print()
    
    if args.force:
        print("⚠️  FORCE MODE: Skipping confirmation prompt!")
        # Simulate the confirmation
        confirm = 'YES'
    else:
        confirm = input("Are you sure you want to delete ALL data? Type 'YES' to confirm: ")
    
    if confirm != 'YES':
        print("Operation cancelled.")
        return
    
    success = clear_database(db_config)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Database clear completed successfully!")
        print("You can now run data ingestion with a fresh database.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Database clear failed!")
        print("Please check the error messages above.")
        print("=" * 60)

if __name__ == "__main__":
    main()
