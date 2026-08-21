from __future__ import annotations

from collections.abc import Sequence

import fitz

from backend.config import settings
from backend.domain.evidence import (
    CURRENT_INGESTION_VERSION,
    make_chunk_id,
    make_content_hash,
)


def extract_pages_from_pdf(pdf_path: str) -> list[dict[str, int | str]]:
    """Extract page text without losing the source page boundaries."""
    document = fitz.open(pdf_path)
    try:
        return [
            {"page_number": page_number, "text": page.get_text()}
            for page_number, page in enumerate(document, start=1)
        ]
    finally:
        document.close()


def extract_text_from_pdf(pdf_path: str) -> str:
    """Backward-compatible full-text extraction helper."""
    return "\n\n".join(str(page["text"]) for page in extract_pages_from_pdf(pdf_path))


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 128) -> list[str]:
    """Split text by character count; chunk_size/overlap are characters."""
    _validate_window(chunk_size, overlap)
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def chunk_paper(
    pdf_path: str,
    *,
    paper_id: str = "unknown",
    chunk_size: int = settings.chunk_size,
    overlap: int = settings.chunk_overlap,
    ingestion_version: str = CURRENT_INGESTION_VERSION,
) -> list[dict]:
    """Chunk PDF text across pages and return traceable serializable records."""
    pages = extract_pages_from_pdf(pdf_path)
    return chunk_pages(
        pages,
        paper_id=paper_id,
        chunk_size=chunk_size,
        overlap=overlap,
        ingestion_version=ingestion_version,
    )


def chunk_pages(
    pages: Sequence[dict[str, int | str]],
    *,
    paper_id: str,
    chunk_size: int = settings.chunk_size,
    overlap: int = settings.chunk_overlap,
    ingestion_version: str = CURRENT_INGESTION_VERSION,
) -> list[dict]:
    """Build character windows while mapping every window back to page range."""
    _validate_window(chunk_size, overlap)
    non_empty_pages = [
        (int(page["page_number"]), str(page.get("text", "")))
        for page in pages
        if str(page.get("text", "")).strip()
    ]
    if not non_empty_pages:
        return []

    combined: list[str] = []
    ranges: list[tuple[int, int, int]] = []
    cursor = 0
    for index, (page_number, text) in enumerate(non_empty_pages):
        if index:
            combined.append("\n\n")
            cursor += 2
        start = cursor
        combined.append(text)
        cursor += len(text)
        ranges.append((start, cursor, page_number))

    full_text = "".join(combined)
    raw_chunks = chunk_text(full_text, chunk_size=chunk_size, overlap=overlap)
    chunks: list[dict] = []
    start = 0
    for chunk_index, content in enumerate(raw_chunks):
        end = start + len(content)
        page_numbers = [
            page_number
            for page_start, page_end, page_number in ranges
            if page_end > start and page_start < end
        ]
        if not page_numbers:
            start = end - overlap if end < len(full_text) else end
            continue
        page_start = min(page_numbers)
        page_end = max(page_numbers)
        content_hash = make_content_hash(content)
        chunks.append(
            {
                "chunk_id": make_chunk_id(
                    paper_id=paper_id,
                    ingestion_version=ingestion_version,
                    content_hash=content_hash,
                    chunk_index=chunk_index,
                    page_start=page_start,
                    page_end=page_end,
                ),
                "paper_id": paper_id,
                "content": content,
                "chunk_index": chunk_index,
                "total_chunks": len(raw_chunks),
                "page_start": page_start,
                "page_end": page_end,
                "content_type": "pdf",
                "ingestion_version": ingestion_version,
                "content_hash": content_hash,
            }
        )
        start = end - overlap if end < len(full_text) else end
    return chunks


def abstract_chunk(
    *,
    paper_id: str,
    title: str,
    abstract: str,
    ingestion_version: str = CURRENT_INGESTION_VERSION,
) -> dict | None:
    content = "\n\n".join(
        part for part in [
            "[Abstract-only -- no full text available]",
            f"Title: {title}" if title else "",
            f"Abstract: {abstract}" if abstract else "",
        ]
        if part
    ).strip()
    if not content:
        return None
    content_hash = make_content_hash(content)
    return {
        "chunk_id": make_chunk_id(
            paper_id=paper_id,
            ingestion_version=ingestion_version,
            content_hash=content_hash,
            chunk_index=0,
            page_start=None,
            page_end=None,
        ),
        "paper_id": paper_id,
        "content": content,
        "chunk_index": 0,
        "total_chunks": 1,
        "page_start": None,
        "page_end": None,
        "content_type": "abstract",
        "ingestion_version": ingestion_version,
        "content_hash": content_hash,
    }


def _validate_window(chunk_size: int, overlap: int) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")
