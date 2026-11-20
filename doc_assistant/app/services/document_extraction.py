"""Document text extraction service supporting PDF, text, and markdown files."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """Normalize extracted text by stripping null bytes and excess whitespace."""
    if not text:
        return ""
    # Strip null bytes and control chars (except standard newlines/tabs)
    cleaned = text.replace("\x00", "")
    # Normalize multiple newlines/spaces
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def extract_pdf_pages(file_path: str | Path) -> List[Dict[str, Any]]:
    """Extract text from a PDF file preserving 1-based page numbers using PyMuPDF (fitz)."""
    import fitz  # PyMuPDF

    pages_data: List[Dict[str, Any]] = []
    file_path = str(file_path)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    doc = fitz.open(file_path)
    try:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            raw_text = page.get_text("text") or ""
            normalized = normalize_text(raw_text)
            pages_data.append({
                "page_number": page_idx + 1,  # 1-based page indexing
                "text": normalized,
            })
    finally:
        doc.close()

    return pages_data


def extract_text_pages(file_path: str | Path) -> List[Dict[str, Any]]:
    """Extract plain text/markdown file, treating content as single page 1."""
    file_path = str(file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    normalized = normalize_text(content)
    return [
        {
            "page_number": 1,
            "text": normalized,
        }
    ]


def extract_pages(file_path: str | Path, mime_type: str) -> List[Dict[str, Any]]:
    """Extract page-level text based on file MIME type or extension.
    
    Returns list of dicts: [{'page_number': int, 'text': str}]
    """
    path_obj = Path(file_path)
    ext = path_obj.suffix.lower()

    if mime_type == "application/pdf" or ext == ".pdf":
        return extract_pdf_pages(file_path)
    elif mime_type in ("text/plain", "text/markdown", "text/x-markdown", "application/json") or ext in (".txt", ".md", ".json"):
        return extract_text_pages(file_path)
    else:
        # Fallback attempt based on content
        try:
            return extract_pdf_pages(file_path)
        except Exception:
            return extract_text_pages(file_path)


def extract_text(file_path: str | Path, mime_type: str = "") -> str:
    """Legacy/convenience function that returns the full joined text."""
    pages = extract_pages(file_path, mime_type)
    return "\n\n".join(p["text"] for p in pages if p["text"])
