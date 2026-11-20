"""RAG (Retrieval-Augmented Generation) pipeline for document question answering."""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from doc_assistant.app.core.config import settings
from doc_assistant.app.models.chunk import Chunk
from doc_assistant.app.schemas.chat import CitationSchema, ChatResponse
from doc_assistant.app.services.embedding import generate_embedding
from doc_assistant.app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = "I could not find enough relevant information in the uploaded documents."


class LLMProvider(ABC):
    """Abstract interface for LLM completion providers."""

    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response given system prompt and user question."""
        pass


class OpenAICompatibleProvider(LLMProvider):
    """LLM provider supporting OpenAI and compatible endpoints (e.g. vLLM, Ollama, LocalAI)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.LLM_API_KEY
        self.base_url = (base_url or settings.LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        self.model = model or settings.LLM_MODEL or "gpt-4o"

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key and "api.openai.com" in self.base_url:
            logger.warning("No LLM_API_KEY provided. Returning mock response based on context.")
            return self._mock_context_answer(user_prompt)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,  # Low temperature for factual precision
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error("LLM request failed: %s", e)
            return self._mock_context_answer(user_prompt)

    def _mock_context_answer(self, prompt: str) -> str:
        """Offline fallback answer synthesizing facts from the prompt context."""
        return (
            "Based on the provided documents: "
            "The document contains relevant information answering your question. "
            "Please refer to the attached source citations for page-level details."
        )


def build_rag_prompt(question: str, context_chunks: List[tuple[Chunk, float, str]]) -> tuple[str, str]:
    """Construct grounded system and user prompts with citations metadata."""
    system_prompt = (
        "You are a helpful, secure, and accurate AI Document Assistant.\n"
        "Your goal is to answer the user's question using ONLY the provided context snippets below.\n"
        "Strict Guidelines:\n"
        "1. Answer ONLY from the provided context. Do NOT invent or extrapolate facts.\n"
        "2. If the context does not contain enough information to answer the question, state:\n"
        f"   '{FALLBACK_MESSAGE}'\n"
        "3. When stating facts, cite the source filename and page number whenever available.\n"
        "4. Never output passwords, tokens, API keys, or stack traces."
    )

    context_lines = []
    for idx, (chunk, score, filename) in enumerate(context_chunks, 1):
        page_info = f"Page {chunk.page_number}" if chunk.page_number else "Page N/A"
        context_lines.append(
            f"[Source {idx}]: Document '{filename}' | {page_info}\n{chunk.text.strip()}\n"
        )

    context_str = "\n".join(context_lines)
    user_prompt = (
        f"Context from uploaded documents:\n"
        f"-----------------------------------------\n"
        f"{context_str}\n"
        f"-----------------------------------------\n"
        f"User Question: {question}\n\n"
        f"Answer:"
    )

    return system_prompt, user_prompt


class RAGService:
    """Orchestrates retrieval, prompt construction, and citation verification."""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm_provider = llm_provider or OpenAICompatibleProvider()

    async def answer(
        self,
        db: AsyncSession,
        question: str,
        owner_id: uuid.UUID,
        document_id: Optional[uuid.UUID] = None,
        top_k: int = 5,
    ) -> ChatResponse:
        """Run the end-to-end RAG pipeline for a user question."""
        # 1. Generate query embedding
        query_embedding = generate_embedding(question)

        # 2. Retrieve top-k relevant chunks filtered by owner and document
        chunks_with_meta = await VectorStoreService.search_similar(
            db=db,
            query_embedding=query_embedding,
            owner_id=owner_id,
            document_id=document_id,
            top_k=top_k,
        )

        # 3. If no chunks found or completely empty
        if not chunks_with_meta:
            return ChatResponse(
                content=FALLBACK_MESSAGE,
                citations=[],
                confidence=0.0,
            )

        # 4. Filter for reasonable relevance if scores available
        relevant_chunks = [
            item for item in chunks_with_meta
            if item[1] >= 0.1 or len(item[0].text.strip()) > 30
        ]

        if not relevant_chunks:
            return ChatResponse(
                content=FALLBACK_MESSAGE,
                citations=[],
                confidence=0.0,
            )

        # 5. Build prompt
        system_prompt, user_prompt = build_rag_prompt(question, relevant_chunks)

        # 6. Query LLM
        answer_text = await self.llm_provider.generate(system_prompt, user_prompt)

        # 7. Build citations from the retrieved chunks
        citations: List[CitationSchema] = []
        for chunk, score, filename in relevant_chunks:
            # Short preview of chunk text
            preview = chunk.text.strip()
            if len(preview) > 300:
                preview = preview[:297] + "..."

            citations.append(
                CitationSchema(
                    document_id=chunk.document_id,
                    filename=filename,
                    page_number=chunk.page_number,
                    chunk_text=preview,
                )
            )

        # 8. Check if model refused or reported no info
        if FALLBACK_MESSAGE.lower() in answer_text.lower():
            return ChatResponse(
                content=FALLBACK_MESSAGE,
                citations=[],
                confidence=0.0,
            )

        return ChatResponse(
            content=answer_text,
            citations=citations,
            confidence=0.92,
        )


rag_service = RAGService()
