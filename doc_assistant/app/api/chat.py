"""Conversations & Chat API router supporting grounded RAG responses with citations."""

from __future__ import annotations

import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from doc_assistant.app.core.database import get_db
from doc_assistant.app.core.security import get_current_user
from doc_assistant.app.models.conversation import Conversation, Message
from doc_assistant.app.models.user import User
from doc_assistant.app.schemas.chat import (
    ChatResponse,
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from doc_assistant.app.services.rag import rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["Chat & Conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED, summary="Create a new conversation")
async def create_conversation(
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a new conversation thread, optionally tied to a specific document."""
    convo = Conversation(
        owner_id=current_user.id,
        document_id=payload.document_id,
        title=payload.title or "New Conversation",
    )
    db.add(convo)
    await db.commit()
    await db.refresh(convo)

    logger.info("Created conversation", extra={"conversation_id": str(convo.id), "user_id": str(current_user.id)})
    return convo


@router.get("", response_model=List[ConversationResponse], summary="List user's conversations")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all conversations belonging to the authenticated user."""
    stmt = (
        select(Conversation)
        .where(Conversation.owner_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )
    result = await db.execute(stmt)
    convos = result.scalars().all()
    return convos


@router.get("/{conversation_id}", response_model=ConversationResponse, summary="Get conversation with messages")
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full conversation details including all messages."""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    convo = result.scalar_one_or_none()

    if not convo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    if convo.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not own this conversation.",
        )

    return convo


@router.post("/{conversation_id}/messages", response_model=ChatResponse, summary="Send message & get RAG response")
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Post a user message, run retrieval-augmented generation, and return grounded answer with citations."""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    convo = result.scalar_one_or_none()

    if not convo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    if convo.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not own this conversation.",
        )

    # 1. Save user message to database
    user_msg = Message(
        conversation_id=convo.id,
        role="user",
        content=payload.content.strip(),
        citations=None,
    )
    db.add(user_msg)

    # 2. Run grounded RAG answering
    chat_response = await rag_service.answer(
        db=db,
        question=payload.content.strip(),
        owner_id=current_user.id,
        document_id=convo.document_id,
    )

    # 3. Save assistant reply with citations to database
    citations_data = [c.model_dump(mode="json") for c in chat_response.citations] if chat_response.citations else None
    assistant_msg = Message(
        conversation_id=convo.id,
        role="assistant",
        content=chat_response.content,
        citations=citations_data,
    )
    db.add(assistant_msg)

    # Auto-update conversation title from first user query if still default
    if convo.title == "New Conversation" and len(payload.content.strip()) > 0:
        convo.title = payload.content.strip()[:40] + ("..." if len(payload.content.strip()) > 40 else "")
        db.add(convo)

    await db.commit()

    logger.info(
        "Chat answer generated with citations",
        extra={
            "conversation_id": str(convo.id),
            "citations_count": len(chat_response.citations),
        },
    )

    return chat_response


@router.delete("/{conversation_id}", status_code=status.HTTP_200_OK, summary="Delete conversation")
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and its messages."""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    convo = result.scalar_one_or_none()

    if not convo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    if convo.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you do not own this conversation.",
        )

    await db.delete(convo)
    await db.commit()

    return {"message": "Conversation deleted successfully."}
