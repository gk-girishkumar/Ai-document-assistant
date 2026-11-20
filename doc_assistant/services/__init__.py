"""Compatibility re-exports for doc_assistant.services."""

from doc_assistant.app.services import (
    auth_service,
    chunking,
    document_extraction,
    embedding,
    rag,
    vector_store,
)

__all__ = [
    "auth_service",
    "chunking",
    "document_extraction",
    "embedding",
    "rag",
    "vector_store",
]
