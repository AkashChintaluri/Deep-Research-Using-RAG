#!/usr/bin/env python3
"""
Document Chunking Module for ArXiv Data Processing
==================================================

This module handles splitting documents into manageable chunks for better searchability
and context preservation. It supports configurable chunk sizes and overlap.

Key Features:
- Token-based chunking with configurable size (200-600 tokens)
- Overlap support (50-100 tokens) for context preservation
- Metadata preservation for each chunk
- Support for both text and abstract chunking
- Efficient processing of large datasets
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import tqdm
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('document_chunking.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ChunkConfig:
    """Configuration for document chunking."""
    min_chunk_size: int = 200
    max_chunk_size: int = 600
    overlap_size: int = 75  # Average of 50-100
    chunk_field: str = 'abstract'  # Field to chunk (abstract or body)
    preserve_sentences: bool = True  # Try to preserve sentence boundaries
    max_workers: int = None  # Number of parallel workers (None = auto-detect)


class Tokenizer:
    """Simple tokenizer for counting tokens in text."""
    
    @staticmethod
    def count_tokens(text: str) -> int:
        """
        Count tokens in text using simple whitespace splitting.
        
        Args:
            text: Input text to tokenize
            
        Returns:
            Number of tokens
        """
        if not text:
            return 0
        return len(text.split())
    
    @staticmethod
    def split_into_tokens(text: str) -> List[str]:
        """
        Split text into tokens.
        
        Args:
            text: Input text to tokenize
            
        Returns:
            List of tokens
        """
        if not text:
            return []
        return text.split()
    
    @staticmethod
    def find_sentence_boundaries(text: str) -> List[int]:
        """
        Find sentence boundary positions in text.
        
        Args:
            text: Input text
            
        Returns:
            List of character positions where sentences end
        """
        # Simple sentence boundary detection
        sentence_endings = re.finditer(r'[.!?]+\s+', text)
        boundaries = []
        for match in sentence_endings:
            boundaries.append(match.end())
        return boundaries


class DocumentChunker:
    """Handles document chunking with metadata preservation."""
    
    def __init__(self, config: ChunkConfig = None):
        """
        Initialize the document chunker.
        
        Args:
            config: Chunking configuration
        """
        self.config = config or ChunkConfig()
        self.tokenizer = Tokenizer()
        self.chunk_count = 0
        
    def chunk_document(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chunk a single document into multiple chunks.
        
        Args:
            document: Document dictionary with metadata
            
        Returns:
            List of chunk dictionaries with metadata
        """
        chunks = []
        
        # Get the text to chunk
        text_to_chunk = document.get(self.config.chunk_field, '')
        if not text_to_chunk:
            logger.warning(f"No text found in field '{self.config.chunk_field}' for document {document.get('id', 'unknown')}")
            return chunks
        
        # Extract metadata
        doc_id = document.get('id', '')
        title = document.get('title', '')
        authors = document.get('authors', '')
        version = document.get('version', '')
        
        # Tokenize the text
        tokens = self.tokenizer.split_into_tokens(text_to_chunk)
        total_tokens = len(tokens)
        
        if total_tokens <= self.config.min_chunk_size:
            # Document is too short, create single chunk
            chunk = self._create_chunk(
                doc_id=doc_id,
                chunk_id=f"{doc_id}_chunk_0",
                text=text_to_chunk,
                start_offset=0,
                end_offset=len(text_to_chunk),
                title=title,
                authors=authors,
                version=version,
                chunk_index=0,
                total_chunks=1
            )
            chunks.append(chunk)
            return chunks
        
        # Find sentence boundaries if preserving sentences
        sentence_boundaries = []
        if self.config.preserve_sentences:
            sentence_boundaries = self.tokenizer.find_sentence_boundaries(text_to_chunk)
        
        # Create chunks with overlap
        start_pos = 0
        chunk_index = 0
        
        while start_pos < total_tokens:
            # Calculate end position for this chunk
            end_pos = min(start_pos + self.config.max_chunk_size, total_tokens)
            
            # Adjust end position to respect sentence boundaries if possible
            if self.config.preserve_sentences and sentence_boundaries:
                # Find the best sentence boundary within the chunk
                chunk_text = ' '.join(tokens[start_pos:end_pos])
                best_boundary = self._find_best_sentence_boundary(
                    chunk_text, sentence_boundaries, start_pos, end_pos
                )
                if best_boundary:
                    end_pos = best_boundary
            
            # Ensure minimum chunk size
            if end_pos - start_pos < self.config.min_chunk_size:
                end_pos = min(start_pos + self.config.min_chunk_size, total_tokens)
            
            # Extract chunk text
            chunk_tokens = tokens[start_pos:end_pos]
            chunk_text = ' '.join(chunk_tokens)
            
            # Calculate character offsets
            char_start = self._get_char_offset(text_to_chunk, tokens, start_pos)
            char_end = self._get_char_offset(text_to_chunk, tokens, end_pos)
            
            # Create chunk
            chunk = self._create_chunk(
                doc_id=doc_id,
                chunk_id=f"{doc_id}_chunk_{chunk_index}",
                text=chunk_text,
                start_offset=char_start,
                end_offset=char_end,
                title=title,
                authors=authors,
                version=version,
                chunk_index=chunk_index,
                total_chunks=0  # Will be updated later
            )
            chunks.append(chunk)
            
            # Move to next chunk with overlap
            start_pos = end_pos - self.config.overlap_size
            chunk_index += 1
            
            # Prevent infinite loop
            if start_pos >= total_tokens - self.config.min_chunk_size:
                break
        
        # Update total chunks count
        for chunk in chunks:
            chunk['total_chunks'] = len(chunks)
        
        self.chunk_count += len(chunks)
        return chunks
    
    def _create_chunk(self, doc_id: str, chunk_id: str, text: str, start_offset: int, 
                     end_offset: int, title: str, authors: str, version: str,
                     chunk_index: int, total_chunks: int) -> Dict[str, Any]:
        """
        Create a chunk dictionary with all required metadata.
        
        Args:
            doc_id: Document ID
            chunk_id: Unique chunk ID
            text: Chunk text content
            start_offset: Character start offset in original document
            end_offset: Character end offset in original document
            title: Document title
            authors: Document authors
            version: Document version
            chunk_index: Index of this chunk in the document
            total_chunks: Total number of chunks in the document
            
        Returns:
            Chunk dictionary with metadata
        """
        return {
            'doc_id': doc_id,
            'chunk_id': chunk_id,
            'chunk_index': chunk_index,
            'total_chunks': total_chunks,
            'text': text,
            'start_offset': start_offset,
            'end_offset': end_offset,
            'title': title,
            'authors': authors,
            'version': version,
            'token_count': self.tokenizer.count_tokens(text),
            'char_count': len(text)
        }
    
    def _find_best_sentence_boundary(self, chunk_text: str, sentence_boundaries: List[int],
                                   start_pos: int, end_pos: int) -> Optional[int]:
        """
        Find the best sentence boundary within a chunk.
        
        Args:
            chunk_text: Text of the current chunk
            sentence_boundaries: List of sentence boundary positions
            start_pos: Token start position
            end_pos: Token end position
            
        Returns:
            Best token position for sentence boundary or None
        """
        # This is a simplified implementation
        # In practice, you'd want more sophisticated sentence boundary detection
        return None
    
    def _get_char_offset(self, text: str, tokens: List[str], token_pos: int) -> int:
        """
        Get character offset for a given token position.
        
        Args:
            text: Original text
            tokens: List of tokens
            token_pos: Token position
            
        Returns:
            Character offset in original text
        """
        if token_pos >= len(tokens):
            return len(text)
        
        # Find the position of the token in the original text
        search_text = ' '.join(tokens[:token_pos])
        if search_text:
            pos = text.find(search_text)
            if pos != -1:
                return pos + len(search_text)
        
        return 0


def chunk_document_parallel(args):
    """Parallel chunking function for multiprocessing."""
    document, config_dict = args
    
    # Recreate config from dict
    config = ChunkConfig(**config_dict)
    chunker = DocumentChunker(config)
    
    # Create chunks
    chunks = chunker.chunk_document(document)
    
    return {
        'document': document,
        'chunks': chunks,
        'chunk_count': len(chunks)
    }


class ChunkingPipeline:
    """Pipeline for processing documents and creating chunks."""
    
    def __init__(self, config: ChunkConfig = None, db_manager=None):
        """
        Initialize the chunking pipeline.
        
        Args:
            config: Chunking configuration
            db_manager: PostgreSQL database manager (optional)
        """
        self.config = config or ChunkConfig()
        self.chunker = DocumentChunker(self.config)
        self.db_manager = db_manager
        self.processed_docs = 0
        self.total_chunks = 0
        
        # Set max workers if not specified
        if self.config.max_workers is None:
            self.config.max_workers = min(cpu_count(), 8)  # Cap at 8 to avoid memory issues
        
    def process_jsonl_file(self, input_file: str, output_file: str, 
                          batch_size: int = 1000) -> None:
        """
        Process a JSONL file and create chunks.
        
        Args:
            input_file: Path to input JSONL file
            output_file: Path to output JSONL file for chunks
            batch_size: Number of documents to process in each batch
        """
        logger.info(f"Starting chunking process for {input_file}")
        
        input_path = Path(input_file)
        output_path = Path(output_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file {input_file} not found")
        
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get total line count for progress bar
        with open(input_path, 'r', encoding='utf-8') as f:
            total_lines = sum(1 for _ in f)
        
        logger.info(f"Processing {total_lines} documents")
        
        with open(input_path, 'r', encoding='utf-8') as infile, \
             open(output_path, 'w', encoding='utf-8') as outfile:
            
            with tqdm.tqdm(total=total_lines, desc="Chunking documents") as pbar:
                batch = []
                
                for line_num, line in enumerate(infile, 1):
                    try:
                        # Parse document
                        document = json.loads(line.strip())
                        
                        # Create chunks
                        chunks = self.chunker.chunk_document(document)
                        
                        if chunks:
                            batch.extend(chunks)
                            self.processed_docs += 1
                            self.total_chunks += len(chunks)
                        
                        # Write batch when it reaches batch_size
                        if len(batch) >= batch_size:
                            self._write_batch(outfile, batch)
                            batch = []
                        
                        pbar.update(1)
                        
                        # Log progress
                        if self.processed_docs % 1000 == 0:
                            logger.info(f"Processed {self.processed_docs} documents, created {self.total_chunks} chunks")
                    
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error at line {line_num}: {str(e)}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing document at line {line_num}: {str(e)}")
                        continue
                
                # Write remaining batch
                if batch:
                    self._write_batch(outfile, batch)
        
        logger.info(f"Chunking completed!")
        logger.info(f"Processed documents: {self.processed_docs}")
        logger.info(f"Total chunks created: {self.total_chunks}")
        logger.info(f"Average chunks per document: {self.total_chunks / max(self.processed_docs, 1):.2f}")
        logger.info(f"Output file: {output_path}")
    
    def process_from_database(self, output_file: str, batch_size: int = 1000, 
                            limit: int = None) -> None:
        """
        Process documents directly from PostgreSQL database and create chunks.
        
        Args:
            output_file: Path to output JSONL file for chunks
            batch_size: Number of documents to process in each batch
            limit: Maximum number of documents to process (None for all)
        """
        if not self.db_manager:
            raise ValueError("Database manager is required for database processing")
        
        logger.info(f"Starting chunking process from database")
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create papers list file
        papers_list_file = output_path.parent / f"{output_path.stem}_papers_list.txt"
        
        # Get total document count
        self.db_manager.cursor.execute("SELECT COUNT(*) as total FROM papers")
        total_docs = self.db_manager.cursor.fetchone()['total']
        
        if limit:
            total_docs = min(total_docs, limit)
        
        logger.info(f"Processing {total_docs} documents from database")
        logger.info(f"Using {self.config.max_workers} parallel workers")
        
        with open(output_path, 'w', encoding='utf-8') as outfile, \
             open(papers_list_file, 'w', encoding='utf-8') as papers_file:
            
            # Write header to papers list
            papers_file.write("Papers Processed for Chunking\n")
            papers_file.write("=" * 50 + "\n")
            papers_file.write(f"Total papers to process: {total_docs}\n")
            papers_file.write(f"Chunking configuration: {self.config.min_chunk_size}-{self.config.max_chunk_size} tokens, {self.config.overlap_size} overlap\n")
            papers_file.write(f"Chunking field: {self.config.chunk_field}\n")
            papers_file.write(f"Parallel workers: {self.config.max_workers}\n")
            papers_file.write("=" * 50 + "\n\n")
            
            with tqdm.tqdm(total=total_docs, desc="Chunking documents") as pbar:
                offset = 0
                batch = []
                
                # Collect all documents first
                all_documents = []
                while offset < total_docs:
                    # Fetch batch of documents
                    query = """
                        SELECT id, title, authors, abstract, body, full_text, version
                        FROM papers 
                        ORDER BY id 
                        LIMIT %s OFFSET %s
                    """
                    self.db_manager.cursor.execute(query, (batch_size, offset))
                    documents = self.db_manager.cursor.fetchall()
                    
                    if not documents:
                        break
                    
                    # Convert to dictionaries
                    for doc in documents:
                        all_documents.append(dict(doc))
                    
                    offset += batch_size
                
                # Process documents in parallel
                config_dict = {
                    'min_chunk_size': self.config.min_chunk_size,
                    'max_chunk_size': self.config.max_chunk_size,
                    'overlap_size': self.config.overlap_size,
                    'chunk_field': self.config.chunk_field,
                    'preserve_sentences': self.config.preserve_sentences
                }
                
                # Prepare arguments for parallel processing
                parallel_args = [(doc, config_dict) for doc in all_documents]
                
                # Process in parallel
                with ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
                    # Submit all tasks
                    future_to_doc = {executor.submit(chunk_document_parallel, args): args[0] for args in parallel_args}
                    
                    # Process completed tasks
                    for future in as_completed(future_to_doc):
                        result = future.result()
                        document = result['document']
                        chunks = result['chunks']
                        chunk_count = result['chunk_count']
                        
                        # Write paper info to papers list
                        papers_file.write(f"Paper {self.processed_docs + 1}:\n")
                        papers_file.write(f"  ID: {document.get('id', 'N/A')}\n")
                        papers_file.write(f"  Title: {document.get('title', 'N/A')}\n")
                        papers_file.write(f"  Authors: {document.get('authors', 'N/A')}\n")
                        papers_file.write(f"  Version: {document.get('version', 'N/A')}\n")
                        papers_file.write(f"  Abstract length: {len(document.get('abstract', ''))} characters\n")
                        papers_file.write(f"  Body length: {len(document.get('body', ''))} characters\n")
                        papers_file.write("-" * 30 + "\n")
                        
                        if chunks:
                            batch.extend(chunks)
                            self.processed_docs += 1
                            self.total_chunks += len(chunks)
                            
                            # Add chunk info to papers list
                            papers_file.write(f"  Chunks created: {len(chunks)}\n")
                            for i, chunk in enumerate(chunks):
                                papers_file.write(f"    Chunk {i+1}: {chunk['token_count']} tokens, {chunk['char_count']} chars\n")
                        else:
                            papers_file.write(f"  Chunks created: 0 (no text to chunk)\n")
                        
                        papers_file.write("\n")
                        pbar.update(1)
                        
                        # Write batch when it reaches batch_size
                        if len(batch) >= batch_size:
                            self._write_batch(outfile, batch)
                            batch = []
                        
                        # Log progress
                        if self.processed_docs % 1000 == 0:
                            logger.info(f"Processed {self.processed_docs} documents, created {self.total_chunks} chunks")
                
                # Write remaining batch
                if batch:
                    self._write_batch(outfile, batch)
            
            # Write summary to papers list
            papers_file.write("\n" + "=" * 50 + "\n")
            papers_file.write("CHUNKING SUMMARY\n")
            papers_file.write("=" * 50 + "\n")
            papers_file.write(f"Total papers processed: {self.processed_docs}\n")
            papers_file.write(f"Total chunks created: {self.total_chunks}\n")
            papers_file.write(f"Average chunks per paper: {self.total_chunks / max(self.processed_docs, 1):.2f}\n")
            papers_file.write(f"Chunks file: {output_path.name}\n")
            papers_file.write(f"Processing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        logger.info(f"Database chunking completed!")
        logger.info(f"Processed documents: {self.processed_docs}")
        logger.info(f"Total chunks created: {self.total_chunks}")
        logger.info(f"Average chunks per document: {self.total_chunks / max(self.processed_docs, 1):.2f}")
        logger.info(f"Output file: {output_path}")
        logger.info(f"Papers list: {papers_list_file}")
    
    def _write_batch(self, outfile, batch: List[Dict[str, Any]]) -> None:
        """
        Write a batch of chunks to the output file.
        
        Args:
            outfile: Output file handle
            batch: List of chunk dictionaries
        """
        for chunk in batch:
            outfile.write(json.dumps(chunk, ensure_ascii=False) + '\n')


def main():
    """Main function for running the chunking pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Chunk documents for better searchability')
    parser.add_argument('--input', '-i', required=True, help='Input JSONL file')
    parser.add_argument('--output', '-o', required=True, help='Output JSONL file for chunks')
    parser.add_argument('--min-chunk-size', type=int, default=200, help='Minimum chunk size in tokens')
    parser.add_argument('--max-chunk-size', type=int, default=600, help='Maximum chunk size in tokens')
    parser.add_argument('--overlap-size', type=int, default=75, help='Overlap size in tokens')
    parser.add_argument('--chunk-field', default='abstract', help='Field to chunk (abstract or body)')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for processing')
    
    args = parser.parse_args()
    
    # Create configuration
    config = ChunkConfig(
        min_chunk_size=args.min_chunk_size,
        max_chunk_size=args.max_chunk_size,
        overlap_size=args.overlap_size,
        chunk_field=args.chunk_field
    )
    
    # Create and run pipeline
    pipeline = ChunkingPipeline(config)
    pipeline.process_jsonl_file(args.input, args.output, args.batch_size)


if __name__ == "__main__":
    main()
