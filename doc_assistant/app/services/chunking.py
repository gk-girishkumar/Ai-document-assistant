"""Text chunking service preserving document pages, positions, and overlap."""

from __future__ import annotations

import re
from typing import List, Dict, Any, Union


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using regex boundary detection."""
    # Split by period, exclamation, question mark followed by whitespace or end of line
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_page_text(
    text: str,
    page_number: int,
    start_chunk_idx: int = 0,
    chunk_size: int = 500,
    overlap: int = 50,
) -> tuple[List[Dict[str, Any]], int]:
    """Chunk a single page's text into overlapping segments."""
    if not text or len(text.strip()) == 0:
        return [], start_chunk_idx

    words = text.split()
    if not words:
        return [], start_chunk_idx

    chunks: List[Dict[str, Any]] = []
    current_idx = start_chunk_idx

    # If the text is short enough, return it as a single chunk if >= 20 chars
    if len(text) <= chunk_size:
        if len(text.strip()) >= 20:
            chunks.append({
                "text": text.strip(),
                "page_number": page_number,
                "chunk_index": current_idx,
            })
            current_idx += 1
        return chunks, current_idx

    # Overlapping window based on character count while respecting word boundaries
    i = 0
    step = max(1, chunk_size - overlap)
    while i < len(text):
        chunk_text = text[i : i + chunk_size].strip()
        # Ensure we don't end mid-word if possible, unless at end of text
        if i + chunk_size < len(text):
            last_space = chunk_text.rfind(" ")
            if last_space > chunk_size // 2:
                chunk_text = chunk_text[:last_space].strip()

        if len(chunk_text) >= 20:
            chunks.append({
                "text": chunk_text,
                "page_number": page_number,
                "chunk_index": current_idx,
            })
            current_idx += 1

        i += step

    return chunks, current_idx


def chunk_text(
    input_data: Union[str, List[Dict[str, Any]]],
    document_id: Any = None,
    chunk_size: int = 500,
    overlap: int = 50,
) -> List[Dict[str, Any]]:
    """Chunk text from raw string or list of page dicts [{'page_number': int, 'text': str}].
    
    Returns list of dicts: [{'text': str, 'page_number': int, 'chunk_index': int}]
    """
    all_chunks: List[Dict[str, Any]] = []
    current_chunk_idx = 0

    if isinstance(input_data, str):
        # Single string with unknown/page 1
        chunks, _ = chunk_page_text(
            text=input_data,
            page_number=1,
            start_chunk_idx=0,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        all_chunks.extend(chunks)
    else:
        # List of page dicts
        for page_info in input_data:
            page_num = page_info.get("page_number", 1)
            page_text = page_info.get("text", "")
            chunks, next_idx = chunk_page_text(
                text=page_text,
                page_number=page_num,
                start_chunk_idx=current_chunk_idx,
                chunk_size=chunk_size,
                overlap=overlap,
            )
            all_chunks.extend(chunks)
            current_chunk_idx = next_idx

    return all_chunks
