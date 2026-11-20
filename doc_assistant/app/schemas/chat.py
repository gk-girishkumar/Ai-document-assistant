"""Chat / Conversation Pydantic v2 schemas."""

from __future__ import annotations

import datetime
import uuid
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Citation ────────────────────────────────────────────────────────────────
class CitationSchema(BaseModel):
    """A single citation referencing a source chunk."""

    document_id: uuid.UUID
    filename: str
    page_number: Optional[int] = None
    chunk_text: str


# ── Conversation ────────────────────────────────────────────────────────────
class ConversationCreate(BaseModel):
    """Payload to create a new conversation."""

    title: str = "New Conversation"
    document_id: Optional[uuid.UUID] = None


class ConversationResponse(BaseModel):
    """Public representation of a conversation."""

    id: uuid.UUID
    owner_id: uuid.UUID
    document_id: Optional[uuid.UUID] = None
    title: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    messages: List["MessageResponse"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ── Message ─────────────────────────────────────────────────────────────────
class MessageCreate(BaseModel):
    """Payload to send a new message in a conversation."""

    content: str = Field(..., min_length=1, max_length=32_000)
    role: str = "user"


class MessageResponse(BaseModel):
    """Public representation of a single message."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    citations: Optional[List[CitationSchema]] = None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


# ── Chat (assistant reply wrapper) ──────────────────────────────────────────
class ChatResponse(BaseModel):
    """Wrapper returned by the chat endpoint, including citations & confidence."""

    content: str
    citations: List[CitationSchema] = Field(default_factory=list)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


# Rebuild forward refs so ConversationResponse can embed MessageResponse.
ConversationResponse.model_rebuild()
