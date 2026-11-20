"""
Celery task for end-to-end document processing.

Pipeline:
    1. Fetch the document record from the database.
    2. Mark status → "processing".
    3. Extract raw text from the file.
    4. Chunk the text into manageable segments.
    5. Generate vector embeddings for each chunk.
    6. Persist chunks + embeddings in the vector store.
    7. Mark status → "completed".

On any failure the status is set to "failed", an error message is recorded,
and the task is retried up to 3 times with exponential back-off.

NOTE: Celery workers are synchronous, so we use plain SQLAlchemy
(``create_engine`` / ``Session``) rather than the async equivalents.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from doc_assistant.workers.celery_app import celery_app

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Synchronous database engine & session factory
# ---------------------------------------------------------------------------
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/doc_assistant",
)

# Ensure we use a synchronous driver — swap asyncpg / aiosqlite URLs if the
# caller accidentally passes an async variant.
_sync_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace(
    "sqlite+aiosqlite://", "sqlite://",
)

engine = create_engine(
    _sync_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Service imports (lazy to avoid circular-import issues at module level)
# ---------------------------------------------------------------------------

def _get_extraction_service():
    """Return the document extraction service module."""
    from doc_assistant.services import document_extraction  # noqa: WPS433
    return document_extraction


def _get_chunking_service():
    """Return the text chunking service module."""
    from doc_assistant.services import chunking  # noqa: WPS433
    return chunking


def _get_embedding_service():
    """Return the embedding generation service module."""
    from doc_assistant.services import embedding  # noqa: WPS433
    return embedding


def _get_vector_store_service():
    """Return the vector store service module."""
    from doc_assistant.services import vector_store  # noqa: WPS433
    return vector_store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _update_document_status(
    session: Session,
    document_id: str,
    status: str,
    error_message: str | None = None,
) -> None:
    """Update the status (and optionally error_message) of a document row."""
    params: dict = {
        "status": status,
        "updated_at": datetime.now(timezone.utc),
        "document_id": document_id,
    }

    if error_message is not None:
        params["error_message"] = error_message
        stmt = text(
            "UPDATE documents "
            "SET status = :status, error_message = :error_message, updated_at = :updated_at "
            "WHERE id = :document_id"
        )
    else:
        stmt = text(
            "UPDATE documents "
            "SET status = :status, updated_at = :updated_at "
            "WHERE id = :document_id"
        )

    session.execute(stmt, params)
    session.commit()
    logger.info(
        "Document %s status updated to '%s'",
        document_id,
        status,
        extra={"document_id": document_id, "status": status},
    )


def _get_document(session: Session, document_id: str) -> dict:
    """Fetch a document row as a dictionary.  Raises ``ValueError`` if not found."""
    row = session.execute(
        text("SELECT * FROM documents WHERE id = :document_id"),
        {"document_id": document_id},
    ).mappings().first()

    if row is None:
        raise ValueError(f"Document {document_id} not found in the database")

    return dict(row)


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    name="doc_assistant.workers.document_worker.process_document",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
    reject_on_worker_lost=True,
    soft_time_limit=540,
    time_limit=600,
)
def process_document(self, document_id: str) -> dict:
    """Process a single document through the full ingestion pipeline.

    Parameters
    ----------
    document_id:
        Primary-key identifier of the document to process.

    Returns
    -------
    dict
        Summary of the processing result including chunk and embedding counts.
    """
    logger.info(
        "Starting document processing",
        extra={"document_id": document_id, "attempt": self.request.retries + 1},
    )

    try:
        # ------------------------------------------------------------------
        # 1. Fetch document record
        # ------------------------------------------------------------------
        with get_sync_session() as session:
            document = _get_document(session, document_id)
        logger.info(
            "Fetched document from DB",
            extra={"document_id": document_id, "filename": document.get("filename")},
        )

        # ------------------------------------------------------------------
        # 2. Mark as "processing"
        # ------------------------------------------------------------------
        with get_sync_session() as session:
            _update_document_status(session, document_id, "processing")

        # ------------------------------------------------------------------
        # 3. Extract text
        # ------------------------------------------------------------------
        logger.info("Extracting text", extra={"document_id": document_id})
        extraction_service = _get_extraction_service()
        doc_path = document.get("stored_path") or document.get("file_path", "")
        extracted_pages = extraction_service.extract_pages(
            file_path=doc_path,
            mime_type=document.get("mime_type", ""),
        )
        total_len = sum(len(p.get("text", "")) for p in extracted_pages)
        logger.info(
            "Text extracted",
            extra={
                "document_id": document_id,
                "text_length": total_len,
                "page_count": len(extracted_pages),
            },
        )

        # ------------------------------------------------------------------
        # 4. Chunk text
        # ------------------------------------------------------------------
        logger.info("Chunking text", extra={"document_id": document_id})
        chunking_service = _get_chunking_service()
        chunks: list[dict] = chunking_service.chunk_text(
            input_data=extracted_pages,
            document_id=document_id,
        )
        logger.info(
            "Text chunked",
            extra={"document_id": document_id, "chunk_count": len(chunks)},
        )

        # ------------------------------------------------------------------
        # 5. Generate embeddings
        # ------------------------------------------------------------------
        logger.info("Generating embeddings", extra={"document_id": document_id})
        embedding_service = _get_embedding_service()
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings: list[list[float]] = embedding_service.generate_embeddings(
            texts=chunk_texts,
        )
        logger.info(
            "Embeddings generated",
            extra={
                "document_id": document_id,
                "embedding_count": len(embeddings),
            },
        )

        # ------------------------------------------------------------------
        # 6. Store chunks with embeddings in the vector store
        # ------------------------------------------------------------------
        logger.info(
            "Storing chunks and embeddings",
            extra={"document_id": document_id},
        )
        vector_store_service = _get_vector_store_service()
        vector_store_service.store_chunks(
            document_id=document_id,
            chunks=chunks,
            embeddings=embeddings,
        )
        logger.info(
            "Chunks and embeddings stored",
            extra={"document_id": document_id, "stored_count": len(chunks)},
        )

        # ------------------------------------------------------------------
        # 7. Mark as "completed"
        # ------------------------------------------------------------------
        with get_sync_session() as session:
            _update_document_status(session, document_id, "completed")

        result = {
            "document_id": document_id,
            "status": "completed",
            "chunk_count": len(chunks),
            "embedding_count": len(embeddings),
        }
        logger.info(
            "Document processing completed successfully",
            extra=result,
        )
        return result

    except ValueError as exc:
        # Document not found — no point retrying.
        logger.error(
            "Document not found, aborting",
            extra={"document_id": document_id, "error": str(exc)},
        )
        raise

    except Exception as exc:
        logger.exception(
            "Document processing failed",
            extra={
                "document_id": document_id,
                "error": str(exc),
                "attempt": self.request.retries + 1,
            },
        )

        # Persist the failure status so the API can report it.
        try:
            with get_sync_session() as session:
                _update_document_status(
                    session,
                    document_id,
                    "failed",
                    error_message=str(exc),
                )
        except Exception:
            logger.exception(
                "Failed to update document status to 'failed'",
                extra={"document_id": document_id},
            )

        # Retry with exponential back-off: 30s, 60s, 120s.
        raise self.retry(
            exc=exc,
            countdown=30 * (2 ** self.request.retries),
        )
