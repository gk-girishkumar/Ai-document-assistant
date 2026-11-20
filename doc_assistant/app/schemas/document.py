"""Document & Chunk Pydantic v2 schemas."""

from __future__ import annotations

import datetime
import uuid
from typing import List, Optional

from pydantic import BaseModel, Field


class ChunkResponse(BaseModel):
    """Public representation of a document chunk."""

    id: uuid.UUID
    document_id: uuid.UUID
    text: str
    page_number: Optional[int] = None
    chunk_index: int
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    """Public representation of a document."""

    id: uuid.UUID
    owner_id: uuid.UUID
    filename: str
    mime_type: str
    file_size: int
    status: str
    error_message: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    chunks: List[ChunkResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    items: List[DocumentResponse]
    total: int
    page: int = 1
    per_page: int = 20


class DocumentUploadResponse(BaseModel):
    """Response returned immediately after a document upload."""

    id: uuid.UUID
    filename: str
    status: str
    message: str = "Document uploaded and queued for processing."

    model_config = {"from_attributes": True}
