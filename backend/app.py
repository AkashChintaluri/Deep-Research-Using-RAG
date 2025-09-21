#!/usr/bin/env python3
"""
RAG Backend Server
=================

FastAPI backend server for the ArXiv RAG system with persistent connections.
"""

import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager

# Add src to path
src_dir = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.api import search_router, health_router, chat_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backend_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    logger.info("Starting RAG Backend Server...")
    logger.info("Backend server startup complete!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down backend server...")
    logger.info("Backend server shutdown complete!")

# Create FastAPI app
app = FastAPI(
    title="ArXiv RAG Backend",
    description="REST API for searching ArXiv astronomy papers using PostgreSQL and Pinecone",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(search_router)
app.include_router(health_router)
app.include_router(chat_router)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "ArXiv RAG Backend API",
        "version": "1.0.0",
        "description": "Now with full RAG capabilities!",
        "endpoints": {
            "chat": "/api/v1/chat",
            "search": "/api/v1/search", 
            "stats": "/api/v1/stats",
            "health": "/api/v1/health",
            "chat_health": "/api/v1/chat/health"
        }
    }

@app.get("/test")
async def test_endpoint():
    """Simple test endpoint."""
    return {"status": "ok", "message": "Backend is working!"}

@app.get("/api/v1/test-health")
async def simple_health():
    """Simple health check without dependencies."""
    return {"status": "healthy", "message": "Simple health check working"}

if __name__ == "__main__":
    print("🚀 Starting ArXiv RAG Backend Server...")
    print("=" * 50)
    
    # Check if virtual environment exists (in current directory)
    venv_path = Path("venv")
    if not venv_path.exists():
        print("❌ Virtual environment not found!")
        print("Please run: python -m venv venv")
        sys.exit(1)
    
    # Add virtual environment to Python path
    venv_site_packages = venv_path / "Lib" / "site-packages"
    if venv_site_packages.exists():
        sys.path.insert(0, str(venv_site_packages))
    
    # Also add the Scripts directory for Windows
    venv_scripts = venv_path / "Scripts"
    if venv_scripts.exists():
        sys.path.insert(0, str(venv_scripts))
    
    # Check if dependencies are installed
    try:
        import fastapi
        import uvicorn
        print("✅ Dependencies found")
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)
    
    print("🌐 Server: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/api/v1/health")
    print("=" * 50)
    print("Press Ctrl+C to stop the server")
    print()
    
    try:
        # Run the server
        uvicorn.run(
            "app:app",
            host="0.0.0.0",
            port=8000,
            reload=False,  # Disable auto-reload to stop change detection
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)