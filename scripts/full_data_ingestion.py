#!/usr/bin/env python3
"""
Full Data Ingestion Script for Codemate
======================================

This script processes the complete 2.8M ArXiv dataset and prepares it for
embedding and vectorization. Includes progress monitoring and error handling.
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.data_processing.data_ingestion_postgres import ArxivDataProcessor
from backend.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('full_ingestion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def estimate_processing_time(total_papers, batch_size=1000):
    """Estimate processing time based on sample performance."""
    # Based on our test: ~900 papers/second
    papers_per_second = 900
    estimated_seconds = total_papers / papers_per_second
    estimated_hours = estimated_seconds / 3600
    return estimated_hours

def monitor_progress(processor, start_time):
    """Monitor processing progress and provide updates."""
    while True:
        try:
            # Get current progress from processor
            processed = getattr(processor, 'processed_count', 0)
            errors = getattr(processor, 'error_count', 0)
            skipped = getattr(processor, 'skipped_count', 0)
            
            if processed > 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                
                # Estimate remaining time
                remaining_papers = 2800000 - processed  # Approximate total
                eta_seconds = remaining_papers / rate if rate > 0 else 0
                eta_hours = eta_seconds / 3600
                
                logger.info(f"📊 Progress: {processed:,} papers processed")
                logger.info(f"⚡ Rate: {rate:.1f} papers/second")
                logger.info(f"⏱️  ETA: {eta_hours:.1f} hours remaining")
                logger.info(f"❌ Errors: {errors}, ⏭️  Skipped: {skipped}")
                logger.info("-" * 50)
            
            time.sleep(30)  # Update every 30 seconds
            
        except KeyboardInterrupt:
            logger.info("🛑 Monitoring stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in monitoring: {e}")
            break

def main():
    """Main function for full data ingestion."""
    print("🚀 Codemate Full Data Ingestion")
    print("=" * 50)
    print("📊 Processing 2.8M ArXiv papers for embedding preparation")
    print("⏱️  Estimated time: 3-4 hours")
    print("💾 Database: PostgreSQL (Codemate)")
    print("=" * 50)
    
    # Check if input file exists
    input_file = "Raw Data/arxiv-metadata-oai-snapshot.json"
    if not Path(input_file).exists():
        logger.error(f"❌ Input file not found: {input_file}")
        return False
    
    # Get file size
    file_size = Path(input_file).stat().st_size / (1024 * 1024 * 1024)  # GB
    logger.info(f"📁 Input file size: {file_size:.2f} GB")
    
    # Configuration
    output_dir = "processed_data"
    batch_size = 1000
    
    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'Codemate',
        'user': 'postgres',
        'password': 'akash'
    }
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Initialize processor
    logger.info("🔧 Initializing data processor...")
    processor = ArxivDataProcessor(input_file, output_dir, db_config)
    
    # Start processing
    logger.info("🚀 Starting full data ingestion...")
    start_time = time.time()
    
    try:
        # Process the full dataset
        processor.process_file_streaming(batch_size)
        
        # Calculate final statistics
        end_time = time.time()
        total_time = end_time - start_time
        total_hours = total_time / 3600
        
        logger.info("🎉 Full data ingestion completed!")
        logger.info(f"⏱️  Total processing time: {total_hours:.2f} hours")
        logger.info(f"📊 Total papers processed: {processor.processed_count:,}")
        logger.info(f"❌ Errors: {processor.error_count}")
        logger.info(f"⏭️  Skipped: {processor.skipped_count}")
        
        # Calculate final rate
        if total_time > 0:
            final_rate = processor.processed_count / total_time
            logger.info(f"⚡ Average processing rate: {final_rate:.1f} papers/second")
        
        logger.info("✅ Database is now ready for embedding and vectorization!")
        
        return True
        
    except KeyboardInterrupt:
        logger.info("🛑 Processing stopped by user")
        logger.info(f"📊 Processed {processor.processed_count:,} papers before stopping")
        return False
        
    except Exception as e:
        logger.error(f"❌ Processing failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Ask for confirmation
    print("\n⚠️  WARNING: This will process 2.8M papers and may take 3-4 hours!")
    print("💾 Make sure you have sufficient disk space and database capacity.")
    
    response = input("\nDo you want to proceed? (yes/no): ").lower().strip()
    
    if response in ['yes', 'y']:
        print("\n🚀 Starting full data ingestion...")
        success = main()
        
        if success:
            print("\n🎉 SUCCESS! Full dataset processed!")
            print("📝 Next steps:")
            print("1. Verify data in database")
            print("2. Proceed with embedding generation")
            print("3. Set up vector search capabilities")
        else:
            print("\n❌ Processing failed or was interrupted")
    else:
        print("\n❌ Operation cancelled")
