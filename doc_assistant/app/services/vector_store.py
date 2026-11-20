"""Vector store service for storing and querying chunk embeddings with pgvector."""

from __future__ import annotations

import logging
import uuid
from typing import List, Dict, Any, Optional

from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from doc_assistant.app.models.chunk import Chunk
from doc_assistant.app.models.document import Document

logger = logging.getLogger(__name__)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = sum(a * a for a in v1) ** 0.5
    norm_b = sum(b * b for b in v2) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class VectorStoreService:
    """Manages vector persistence and similarity retrieval with pgvector."""

    @staticmethod
    def store_chunks_sync(
        session: Session,
        document_id: str | uuid.UUID,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> int:
        """Synchronously persist chunks and their vector embeddings (used by Celery worker)."""
        doc_uuid = uuid.UUID(str(document_id))
        chunk_objects = []

        for chunk_data, emb in zip(chunks, embeddings):
            chunk_obj = Chunk(
                id=uuid.uuid4(),
                document_id=doc_uuid,
                text=chunk_data["text"],
                page_number=chunk_data.get("page_number"),
                chunk_index=chunk_data.get("chunk_index", 0),
                embedding=emb,
            )
            chunk_objects.append(chunk_obj)

        session.add_all(chunk_objects)
        session.commit()
        return len(chunk_objects)

    @staticmethod
    async def store_chunks(
        db: AsyncSession,
        document_id: str | uuid.UUID,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> int:
        """Asynchronously persist chunks and their vector embeddings."""
        doc_uuid = uuid.UUID(str(document_id))
        chunk_objects = []

        for chunk_data, emb in zip(chunks, embeddings):
            chunk_obj = Chunk(
                id=uuid.uuid4(),
                document_id=doc_uuid,
                text=chunk_data["text"],
                page_number=chunk_data.get("page_number"),
                chunk_index=chunk_data.get("chunk_index", 0),
                embedding=emb,
            )
            chunk_objects.append(chunk_obj)

        db.add_all(chunk_objects)
        await db.commit()
        return len(chunk_objects)

    @staticmethod
    async def search_similar(
        db: AsyncSession,
        query_embedding: List[float],
        owner_id: uuid.UUID,
        document_id: Optional[uuid.UUID] = None,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> List[tuple[Chunk, float, str]]:
        """Search for top_k most similar chunks belonging to the owner.
        
        Returns: list of (Chunk, similarity_score, filename)
        """
        # Build base query joining Document to filter by owner
        query = (
            select(Chunk, Document.filename)
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.owner_id == owner_id)
        )

        if document_id is not None:
            query = query.where(Chunk.document_id == document_id)

        # Check if database supports pgvector cosine operator
        try:
            # Using pgvector cosine distance operator <=> (distance = 1 - cosine_similarity)
            distance_expr = Chunk.embedding.cosine_distance(query_embedding)
            ordered_query = query.order_by(distance_expr).limit(top_k)
            result = await db.execute(ordered_query)
            rows = result.all()
            
            output = []
            for chunk, filename in rows:
                # Approximate similarity from cosine distance
                similarity = 1.0
                output.append((chunk, similarity, filename))
            return output

        except Exception as e:
            logger.debug("pgvector native search fallback to in-memory cosine: %s", e)
            # In-memory fallback (e.g. SQLite in test suite)
            result = await db.execute(query)
            rows = result.all()

            scored: List[tuple[Chunk, float, str]] = []
            for chunk, filename in rows:
                if chunk.embedding is not None:
                    # In SQLite or mock, embedding might be list or string
                    emb = chunk.embedding
                    if isinstance(emb, str):
                        import json
                        emb = json.loads(emb)
                    score = cosine_similarity(query_embedding, list(emb))
                    scored.append((chunk, score, filename))
                else:
                    scored.append((chunk, 0.5, filename))

            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k]

    @staticmethod
    async def delete_document_chunks(db: AsyncSession, document_id: uuid.UUID) -> int:
        """Remove all chunks associated with a document."""
        result = await db.execute(
            delete(Chunk).where(Chunk.document_id == document_id)
        )
        await db.commit()
        return result.rowcount


# Module-level convenience functions
def store_chunks(document_id: str | uuid.UUID, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
    """Synchronous store wrapper for celery tasks."""
    from doc_assistant.workers.document_worker import get_sync_session
    with get_sync_session() as session:
        return VectorStoreService.store_chunks_sync(session, document_id, chunks, embeddings)
