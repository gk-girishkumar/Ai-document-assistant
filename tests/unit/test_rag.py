"""Unit tests for RAG prompt construction and fallback behavior."""

import uuid
import pytest
from doc_assistant.app.models.chunk import Chunk
from doc_assistant.app.services.rag import (
    build_rag_prompt,
    FALLBACK_MESSAGE,
    RAGService,
    LLMProvider,
)


class MockLLMProvider(LLMProvider):
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        return "The document states that the architecture uses pgvector and FastAPI."


class RefusingLLMProvider(LLMProvider):
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        return FALLBACK_MESSAGE


def test_build_rag_prompt():
    chunk = Chunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        text="FastAPI is a modern web framework for Python.",
        page_number=3,
        chunk_index=0,
    )
    context_chunks = [(chunk, 0.95, "architecture_guide.pdf")]

    system_prompt, user_prompt = build_rag_prompt("What is FastAPI?", context_chunks)

    assert "ONLY from the provided context" in system_prompt
    assert "architecture_guide.pdf" in user_prompt
    assert "Page 3" in user_prompt
    assert "What is FastAPI?" in user_prompt


@pytest.mark.asyncio
async def test_rag_fallback_when_no_context(db_session, test_user):
    user, _ = test_user
    rag = RAGService(llm_provider=MockLLMProvider())

    response = await rag.answer(
        db=db_session,
        question="How does quantum teleportation work in this app?",
        owner_id=user.id,
    )

    assert response.content == FALLBACK_MESSAGE
    assert len(response.citations) == 0
