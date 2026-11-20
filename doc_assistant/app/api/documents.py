"""Documents API router handling file uploads, processing triggers, and chunks retrieval."""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import List

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from doc_assistant.app.core.config import settings
from doc_assistant.app.core.database import get_db
from doc_assistant.app.core.security import get_current_user
from doc_assistant.app.models.chunk import Chunk
from doc_assistant.app.models.document import Document
from doc_assistant.app.models.user import User
from doc_assistant.app.schemas.document import (
    ChunkResponse,
    DocumentResponse,
    DocumentUploadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])

ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/x-markdown": ".md",
}


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and shell exploits."""
    clean = os.path.basename(filename)
    clean = clean.replace("..", "").replace("/", "").replace("\\", "").strip()
    return clean or "unnamed_document"


@router.get("", response_model=List[DocumentResponse], summary="List current user's documents")
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all documents owned by the authenticated user."""
    stmt = (
        select(Document)
        .where(Document.owner_id == current_user.id)
        .order_by(Document.created_at.desc())
    )
    result = await db.execute(stmt)
    documents = result.scalars().all()
    return documents


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new document (PDF, TXT, MD)",
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document file with type and size validation."""
    original_filename = sanitize_filename(file.filename or "uploaded_file")
    mime_type = file.content_type or "application/octet-stream"

    # Validate MIME type or file extension
    ext = Path(original_filename).suffix.lower()
    if mime_type not in ALLOWED_MIME_TYPES and ext not in (".pdf", ".txt", ".md"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{mime_type}'. Supported: PDF, TXT, MD.",
        )

    # Read and validate size
    contents = await file.read()
    file_size = len(contents)
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Ensure upload directory exists
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Store with random UUID name to prevent collisions and path traversal
    file_uuid = uuid.uuid4()
    stored_name = f"{file_uuid}{ext or '.bin'}"
    stored_path = upload_dir / stored_name

    with open(stored_path, "wb") as f:
        f.write(contents)

    # Create Document record
    doc = Document(
        id=file_uuid,
        owner_id=current_user.id,
        filename=original_filename,
        stored_path=str(stored_path),
        mime_type=mime_type,
        file_size=file_size,
        status="pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    logger.info(
        "Document uploaded successfully",
        extra={"document_id": str(doc.id), "user_id": str(current_user.id)},
    )

    return DocumentUploadResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status,
        message="Document uploaded successfully. Processing can now be triggered.",
    )


@router.get("/{document_id}", response_model=DocumentResponse, summary="Get document details")
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve document metadata and chunks."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if doc.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not own this document.",
        )

    return doc


@router.post("/{document_id}/process", summary="Queue document for asynchronous processing")
async def process_document_endpoint(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger background document extraction, chunking, and vector embedding."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if doc.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not own this document.",
        )

    doc.status = "processing"
    doc.error_message = None
    db.add(doc)
    await db.commit()

    # Try Celery dispatch, fallback to FastAPI background task
    try:
        from doc_assistant.workers.document_worker import process_document
        process_document.delay(str(doc.id))
        logger.info("Dispatched to Celery worker", extra={"document_id": str(doc.id)})
    except Exception as e:
        logger.warning("Celery dispatch unavailable (%s), using local background task.", e)
        from doc_assistant.workers.document_worker import process_document
        background_tasks.add_task(process_document, str(doc.id))

    return {
        "document_id": doc.id,
        "status": "processing",
        "message": "Document processing task has been dispatched.",
    }


@router.delete("/{document_id}", status_code=status.HTTP_200_OK, summary="Delete a document")
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document, its stored file on disk, and its embedded chunks."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if doc.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not own this document.",
        )

    if doc.stored_path and os.path.exists(doc.stored_path):
        try:
            os.remove(doc.stored_path)
        except OSError as e:
            logger.warning("Could not delete file %s: %s", doc.stored_path, e)

    await db.delete(doc)
    await db.commit()

    logger.info("Document deleted", extra={"document_id": str(document_id)})
    return {"message": "Document and all associated data deleted successfully."}


@router.get("/{document_id}/chunks", response_model=List[ChunkResponse], summary="List document chunks")
async def get_document_chunks(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all extracted and indexed text chunks for a document."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if doc.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not own this document.",
        )

    chunks_result = await db.execute(
        select(Chunk)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index.asc())
    )
    chunks = chunks_result.scalars().all()
    return chunks
