"""Unit tests for text extraction from text and PDF documents."""

import tempfile
from pathlib import Path
from doc_assistant.app.services.document_extraction import (
    normalize_text,
    extract_pages,
    extract_text,
)


def test_normalize_text():
    raw = "Hello   world \x00 with \t spaces \n\n\n\n and newlines."
    normalized = normalize_text(raw)
    assert "\x00" not in normalized
    assert "   " not in normalized
    assert "\n\n\n" not in normalized
    assert "Hello world with spaces" in normalized


def test_extract_text_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Line 1 of sample text.\nLine 2 of sample text.")
        tmp_path = f.name

    try:
        pages = extract_pages(tmp_path, "text/plain")
        assert len(pages) == 1
        assert pages[0]["page_number"] == 1
        assert "Line 1" in pages[0]["text"]
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_extract_markdown_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Heading 1\nSome detailed notes on RAG systems.")
        tmp_path = f.name

    try:
        pages = extract_pages(tmp_path, "text/markdown")
        assert len(pages) == 1
        assert "Heading 1" in pages[0]["text"]
    finally:
        Path(tmp_path).unlink(missing_ok=True)
