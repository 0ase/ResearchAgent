from pathlib import Path

import fitz

from backend.domain.evidence import CURRENT_INGESTION_VERSION
from backend.services.chunking import chunk_paper


def _make_pdf(path: Path) -> None:
    document = fitz.open()
    for page_number in range(1, 4):
        page = document.new_page()
        page.insert_text(
            (40, 60),
            f"Page {page_number}. "
            + ("This paragraph contains enough text to cross page boundaries. " * 8),
        )
    document.save(path)
    document.close()


def test_pdf_chunks_keep_page_ranges_and_stable_ids(tmp_path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    _make_pdf(pdf_path)

    first = chunk_paper(
        str(pdf_path),
        paper_id="paper-1",
        chunk_size=150,
        overlap=30,
    )
    second = chunk_paper(
        str(pdf_path),
        paper_id="paper-1",
        chunk_size=150,
        overlap=30,
    )

    assert first
    assert [chunk["chunk_id"] for chunk in first] == [chunk["chunk_id"] for chunk in second]
    assert all(chunk["ingestion_version"] == CURRENT_INGESTION_VERSION for chunk in first)
    assert all(chunk["content_type"] == "pdf" for chunk in first)
    assert all(chunk["page_start"] >= 1 for chunk in first)
    assert all(chunk["page_end"] >= chunk["page_start"] for chunk in first)
    assert any(chunk["page_start"] != chunk["page_end"] for chunk in first)


def test_chunking_empty_pdf_text_returns_no_chunks(tmp_path) -> None:
    pdf_path = tmp_path / "empty.pdf"
    document = fitz.open()
    document.new_page()
    document.save(pdf_path)
    document.close()

    assert chunk_paper(str(pdf_path), paper_id="paper-1") == []
