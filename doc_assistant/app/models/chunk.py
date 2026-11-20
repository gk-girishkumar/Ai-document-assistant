"""Chunk ORM model with pgvector embedding support."""

from __future__ import annotations

import datetime
import uuid
from typing import TYPE_CHECKING, Any

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    from sqlalchemy.types import UserDefinedType
    class Vector(UserDefinedType):
        """Fallback Vector type when pgvector is not installed."""
        def __init__(self, dim: int = 384):
            self.dim = dim
        def get_col_spec(self, **kw):
            return f"vector({self.dim})"

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from doc_assistant.app.core.config import settings
from doc_assistant.app.core.database import Base

if TYPE_CHECKING:
    from doc_assistant.app.models.document import Document


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # pgvector column — dimension set from config
    embedding: Mapped[Any] = mapped_column(
        Vector(settings.EMBEDDING_DIM),
        nullable=True,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.utcnow,
        nullable=False,
    )

    # ── Relationships ───────────────────────────────────────────────────
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Chunk id={self.id} doc={self.document_id} index={self.chunk_index}>"
