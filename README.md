# ArXiv RAG System

A complete RAG (Retrieval-Augmented Generation) system for searching ArXiv astronomy papers using PostgreSQL and Pinecone.

## Quick Start

```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py
```

## Project Structure

```
├── backend/           # Main application code
│   ├── app.py        # FastAPI server
│   ├── src/          # Source code
│   ├── scripts/      # Utility scripts
│   ├── data/         # Data files
│   └── logs/         # Log files
└── venv/             # Virtual environment
```

## Features

- **PDF Processing**: Extract text and metadata from ArXiv PDFs
- **Vector Search**: Semantic search using Pinecone and FAISS
- **Database Storage**: PostgreSQL for metadata and full-text search
- **REST API**: FastAPI backend with health checks and search endpoints
- **Hybrid Search**: Combines vector similarity and full-text search

## API Endpoints

- `GET /` - API information
- `GET /api/v1/health` - Health check
- `GET /api/v1/search` - Search papers
- `GET /api/v1/stats` - Database statistics

## Documentation

See `backend/README.md` for detailed documentation.