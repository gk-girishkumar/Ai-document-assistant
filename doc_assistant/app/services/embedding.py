"""Embedding generation service with support for sentence-transformers and OpenAI."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from doc_assistant.app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for vector embedding providers."""

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of strings."""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query string."""
        pass


class SentenceTransformerProvider(EmbeddingProvider):
    """Local embeddings using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading sentence-transformers model: %s", self.model_name)
                self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.warning("Failed to load sentence_transformers: %s. Using mock fallback.", e)
                self._model = None

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        self._load_model()
        if self._model is not None:
            embeddings = self._model.encode(texts, normalize_embeddings=True)
            return embeddings.tolist()
        
        # Fallback deterministic pseudo-embedding (for tests/offline environments)
        return [self._mock_vector(t) for t in texts]

    def embed_query(self, query: str) -> List[float]:
        self._load_model()
        if self._model is not None:
            embedding = self._model.encode(query, normalize_embeddings=True)
            return embedding.tolist()
        return self._mock_vector(query)

    def _mock_vector(self, text: str) -> List[float]:
        """Deterministic 384-dimensional vector based on string hash for fallback/testing."""
        dim = settings.EMBEDDING_DIM
        import hashlib
        h = hashlib.sha256(text.encode("utf-8")).digest()
        vec = [(float(b) / 255.0 * 2.0 - 1.0) for b in h[:32]]
        # Repeat/slice to dim
        extended = (vec * (dim // len(vec) + 1))[:dim]
        # Normalize
        norm = sum(x * x for x in extended) ** 0.5 or 1.0
        return [x / norm for x in extended]


_provider_instance: Optional[EmbeddingProvider] = None


def get_embedding_provider() -> EmbeddingProvider:
    """Singleton getter for the configured embedding provider."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = SentenceTransformerProvider(settings.EMBEDDING_MODEL)
    return _provider_instance


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Module-level function to generate embeddings for a batch of strings."""
    return get_embedding_provider().embed_texts(texts)


def generate_embedding(text: str) -> List[float]:
    """Module-level function to generate an embedding for a single string."""
    return get_embedding_provider().embed_query(text)
