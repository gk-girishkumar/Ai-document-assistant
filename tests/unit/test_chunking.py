"""Unit tests for document text chunking."""

from doc_assistant.app.services.chunking import chunk_text, split_into_sentences


def test_split_into_sentences():
    text = "Hello world. This is sentence two! And sentence three?"
    sentences = split_into_sentences(text)
    assert len(sentences) == 3
    assert sentences[0] == "Hello world."


def test_chunk_single_page():
    page_data = [{"page_number": 1, "text": "This is a document sample text that contains enough words to test the basic chunking functionality properly."}]
    chunks = chunk_text(page_data, chunk_size=100, overlap=20)
    assert len(chunks) >= 1
    assert chunks[0]["page_number"] == 1
    assert chunks[0]["chunk_index"] == 0
    assert len(chunks[0]["text"]) >= 20


def test_chunk_multiple_pages():
    pages = [
        {"page_number": 1, "text": "Page one text content with information about the system architecture and design."},
        {"page_number": 2, "text": "Page two text content covering database vectors and retrieval metrics."},
    ]
    chunks = chunk_text(pages, chunk_size=50, overlap=10)
    page_nums = {c["page_number"] for c in chunks}
    assert 1 in page_nums
    assert 2 in page_nums


def test_chunk_skips_empty():
    pages = [
        {"page_number": 1, "text": "   \n\n   "},
        {"page_number": 2, "text": "Short"},  # < 20 chars
    ]
    chunks = chunk_text(pages)
    assert len(chunks) == 0


def test_chunk_preserves_order():
    text = "Alpha paragraph here. Beta paragraph there. Gamma paragraph follows."
    chunks = chunk_text(text, chunk_size=30, overlap=5)
    for i, c in enumerate(chunks):
        assert c["chunk_index"] == i
