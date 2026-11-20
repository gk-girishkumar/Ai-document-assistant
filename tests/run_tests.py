"""Standalone test runner to verify tests without external pytest dependency."""

import sys
import os
import uuid
import asyncio

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from doc_assistant.app.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from doc_assistant.app.services.chunking import chunk_text, split_into_sentences
from doc_assistant.app.services.document_extraction import normalize_text, extract_pages
from doc_assistant.app.services.vector_store import cosine_similarity
from doc_assistant.app.services.rag import build_rag_prompt, FALLBACK_MESSAGE
from doc_assistant.app.models.chunk import Chunk

def run_all():
    print("========================================")
    print("RUNNING AI DOCUMENT ASSISTANT TEST SUITE")
    print("========================================")
    passed = 0
    failed = 0

    def test(name, func):
        nonlocal passed, failed
        try:
            func()
            print(f"[PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1

    # ── Security tests ──
    print("\n--- Security & Authentication Tests ---")
    def test_hashing():
        pwd = "TestPassword123!"
        h = hash_password(pwd)
        assert verify_password(pwd, h) is True
        assert verify_password("Wrong", h) is False
    test("Password hashing and verification", test_hashing)

    def test_salt_uniqueness():
        pwd = "SamePassword123!"
        h1 = hash_password(pwd)
        h2 = hash_password(pwd)
        assert h1 != h2
        assert verify_password(pwd, h1) and verify_password(pwd, h2)
    test("Password salt uniqueness", test_salt_uniqueness)

    def test_strength():
        assert len(validate_password_strength("ValidP@ssw0rd1")) == 0
        assert len(validate_password_strength("weak")) > 0
    test("Password strength policy validation", test_strength)

    def test_jwt():
        uid = uuid.uuid4()
        token = create_access_token(uid, {"role": "admin"})
        payload = verify_token(token, expected_type="access")
        assert payload["sub"] == str(uid)
        assert payload["role"] == "admin"
    test("JWT access token issue & verify", test_jwt)

    def test_refresh_jwt():
        uid = uuid.uuid4()
        token = create_refresh_token(uid)
        payload = verify_token(token, expected_type="refresh")
        assert payload["sub"] == str(uid)
    test("JWT refresh token issue & verify", test_refresh_jwt)

    # ── Chunking tests ──
    print("\n--- Chunking & Text Processing Tests ---")
    def test_sentences():
        s = split_into_sentences("Sentence one. Sentence two! Sentence three?")
        assert len(s) == 3
    test("Sentence boundary splitting", test_sentences)

    def test_chunking_pages():
        pages = [
            {"page_number": 1, "text": "This is page one text content with information about the system architecture."},
            {"page_number": 2, "text": "This is page two text content covering database vectors and retrieval metrics."},
        ]
        chunks = chunk_text(pages, chunk_size=50, overlap=10)
        assert len(chunks) >= 2
        p_nums = {c["page_number"] for c in chunks}
        assert 1 in p_nums and 2 in p_nums
    test("Page-preserving overlapping chunking", test_chunking_pages)

    # ── Text Extraction tests ──
    print("\n--- Text Extraction Tests ---")
    def test_normalization():
        raw = "Hello   world \x00 with \t spaces \n\n\n\n\n and newlines."
        norm = normalize_text(raw)
        assert "\x00" not in norm
        assert "Hello world with spaces" in norm
    test("Text normalization & null-byte stripping", test_normalization)

    # ── Vector Search tests ──
    print("\n--- Vector Search & Cosine Distance Tests ---")
    def test_cosine():
        assert abs(cosine_similarity([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-5
        assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0]) - 0.0) < 1e-5
        assert abs(cosine_similarity([1.0, 0.0], [-1.0, 0.0]) - (-1.0)) < 1e-5
    test("Cosine similarity calculation", test_cosine)

    # ── RAG Prompt & Grounding tests ──
    print("\n--- Grounded RAG & Citations Tests ---")
    def test_rag():
        c = Chunk(
            id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            text="FastAPI is an async framework with Pydantic validation.",
            page_number=4,
            chunk_index=0,
        )
        sys_p, usr_p = build_rag_prompt("What is FastAPI?", [(c, 0.9, "manual.pdf")])
        assert "ONLY from the provided context" in sys_p
        assert "manual.pdf" in usr_p
        assert "Page 4" in usr_p
    test("Grounded RAG prompt and citation formatting", test_rag)

    print("\n========================================")
    print(f"RESULTS: {passed} PASSED, {failed} FAILED")
    print("========================================")
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_all()
