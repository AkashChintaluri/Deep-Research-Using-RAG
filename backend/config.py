"""
Configuration settings for the Codemate ArXiv Data Processing Backend
"""

import os
from typing import Dict, Any

class Config:
    """Base configuration class."""
    
    # Database settings
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME', 'Codemate')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'akash')
    
    # Data processing settings
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', 1000))
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', 4))
    
    # File paths
    RAW_DATA_DIR = os.getenv('RAW_DATA_DIR', 'Raw Data')
    PROCESSED_DATA_DIR = os.getenv('PROCESSED_DATA_DIR', 'processed_data')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'data_processing.log')
    
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
