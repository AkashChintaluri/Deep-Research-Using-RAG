"""
Embedding service for generating text embeddings.
"""

import logging
from typing import List

from ..core.config import Config
from .embedding_generation import EmbeddingGenerator, EmbeddingConfig

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating text embeddings with model caching."""
    
    _instance = None
    _model = None
    
    def __new__(cls):
        """Singleton pattern to ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.generator = None
            self._initialize()
            self.initialized = True
    
    def _initialize(self):
        """Initialize the embedding generator with cached model."""
        try:
            # Use cached model if available
            if EmbeddingService._model is not None:
                config = EmbeddingConfig(model_name=Config.EMBEDDING_MODEL_NAME)
                self.generator = EmbeddingGenerator(config)
                self.generator.model = EmbeddingService._model
                logger.info("[OK] Embedding service initialized with cached model!")
            else:
                # Load model for the first time
                config = EmbeddingConfig(model_name=Config.EMBEDDING_MODEL_NAME)
                self.generator = EmbeddingGenerator(config)
                # Cache the model for future use
                EmbeddingService._model = self.generator.model
                logger.info("[OK] Embedding service initialized and model cached!")
        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        try:
            return self.generator.generate_embedding(text)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
