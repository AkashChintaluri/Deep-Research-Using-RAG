"""
Configuration settings for the Codemate ArXiv Data Processing Backend
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class with hardcoded safe values."""
    
    # Database settings (only sensitive values from environment)
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'akash')
    
    # Hardcoded database settings (safe to hardcode)
    DB_PORT = 5432
    DB_NAME = "arxiv"
    
    # Hardcoded data processing settings
    BATCH_SIZE = 1000
    MAX_WORKERS = 4
    
    # Hardcoded file paths
    RAW_DATA_DIR = "Raw Data"
    PROCESSED_DATA_DIR = "processed_data"
    
    # Hardcoded logging settings
    LOG_LEVEL = "INFO"
    LOG_FILE = "data_processing.log"
    
    # Hardcoded embedding settings
    EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_BATCH_SIZE = 32
    EMBEDDING_NORMALIZE_VECTORS = True
    EMBEDDING_VECTOR_DIMENSION = 384
    
    # Hardcoded FAISS settings
    FAISS_INDEX_TYPE = "IndexFlatIP"
    FAISS_METADATA_FILE = "processed_data/faiss_metadata.jsonl"
    FAISS_INDEX_FILE = "processed_data/faiss_index.bin"
    
    # Pinecone settings (only API key from environment)
    PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
    
    # Hardcoded Pinecone settings
    PINECONE_ENVIRONMENT = "us-east-1-aws"
    PINECONE_INDEX_NAME = "arxiv-papers"
    PINECONE_DIMENSION = 384
    PINECONE_METRIC = "cosine"
    PINECONE_CLOUD = "aws"
    PINECONE_REGION = "us-east-1"
    
    # OpenAI/LLM settings (only API key from environment)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Hardcoded OpenAI settings
    OPENAI_MODEL = "gpt-4o"
    OPENAI_MAX_TOKENS = 800
    OPENAI_TEMPERATURE = 0.5
    OPENAI_TIMEOUT = 15
    
    # Azure OpenAI settings (only sensitive values from environment)
    AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
    AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
    
    # Hardcoded Azure OpenAI settings
    AZURE_OPENAI_API_VERSION = "2025-01-01-preview"
    AZURE_OPENAI_DEPLOYMENT = "gpt-4o"
    USE_AZURE_OPENAI = os.getenv('USE_AZURE_OPENAI', 'true').lower() == 'true'  # Default to Azure
    
    @classmethod
    def get_database_config(cls) -> Dict[str, Any]:
        """Get database configuration as dictionary."""
        return {
            'host': cls.DB_HOST,
            'port': cls.DB_PORT,
            'database': cls.DB_NAME,
            'user': cls.DB_USER,
            'password': cls.DB_PASSWORD
        }
    
    
    @classmethod
    def get_embedding_config(cls) -> Dict[str, Any]:
        """Get embedding configuration as dictionary."""
        return {
            'model_name': cls.EMBEDDING_MODEL_NAME,
            'batch_size': cls.EMBEDDING_BATCH_SIZE,
            'normalize_vectors': cls.EMBEDDING_NORMALIZE_VECTORS,
            'vector_dimension': cls.EMBEDDING_VECTOR_DIMENSION
        }
    
    @classmethod
    def get_pinecone_config(cls) -> Dict[str, Any]:
        """Get Pinecone configuration as dictionary."""
        return {
            'api_key': cls.PINECONE_API_KEY,
            'environment': cls.PINECONE_ENVIRONMENT,
            'index_name': cls.PINECONE_INDEX_NAME,
            'dimension': cls.PINECONE_DIMENSION,
            'metric': cls.PINECONE_METRIC,
            'cloud': cls.PINECONE_CLOUD,
            'region': cls.PINECONE_REGION
        }
    
    @classmethod
    def get_openai_config(cls) -> Dict[str, Any]:
        """Get OpenAI configuration as dictionary."""
        return {
            'api_key': cls.OPENAI_API_KEY,
            'model': cls.OPENAI_MODEL,
            'max_tokens': cls.OPENAI_MAX_TOKENS,
            'temperature': cls.OPENAI_TEMPERATURE,
            'timeout': cls.OPENAI_TIMEOUT
        }
    
    @classmethod
    def get_azure_openai_config(cls) -> Dict[str, Any]:
        """Get Azure OpenAI configuration as dictionary."""
        return {
            'endpoint': cls.AZURE_OPENAI_ENDPOINT,
            'api_key': cls.AZURE_OPENAI_API_KEY,
            'api_version': cls.AZURE_OPENAI_API_VERSION,
            'deployment': cls.AZURE_OPENAI_DEPLOYMENT,
            'use_azure': cls.USE_AZURE_OPENAI
        }

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    LOG_LEVEL = 'WARNING'

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
