import pytest

import backend.rag.ingestion as ingestion
from backend.domain.evidence import CURRENT_INGESTION_VERSION


class FakeRepository:
    def __init__(self, existing=None) -> None:
        self.existing = existing or []
        self.saved = []

    async def list_for_paper(self, _paper_id, _version):
        return self.existing

    async def upsert_chunks(self, paper_id, chunks):
        self.saved.append((paper_id, list(chunks)))
        return chunks


@pytest.mark.asyncio
async def test_missing_embedding_key_keeps_sqlite_chunks(monkeypatch) -> None:
    repository = FakeRepository()

    async def no_pdf(_paper):
        return None

    async def fail_if_called(_texts):
        raise AssertionError("Embedding must be skipped without a key")

    monkeypatch.setattr(ingestion, "download_pdf", no_pdf)
    monkeypatch.setattr(ingestion, "embed_texts", fail_if_called)
    monkeypatch.setattr(ingestion.settings, "dashscope_api_key", "")

    result = await ingestion.ingest_paper(
        {
            "paper_id": "paper-1",
            "title": "A paper",
            "abstract": "A real abstract.",
        },
        chunk_repository=repository,
    )

    assert result.readable is True
    assert result.vector_indexed is False
    assert result.chunk_count == 1
    assert "EMBEDDING_NOT_CONFIGURED" in result.warnings
    assert repository.saved[0][1][0]["ingestion_version"] == CURRENT_INGESTION_VERSION


@pytest.mark.asyncio
async def test_embedding_failure_does_not_remove_persisted_chunks(monkeypatch) -> None:
    repository = FakeRepository()

    async def no_pdf(_paper):
        return None

    async def fail_embed(_texts):
        raise RuntimeError("embedding service unavailable")

    monkeypatch.setattr(ingestion, "download_pdf", no_pdf)
    monkeypatch.setattr(ingestion, "embed_texts", fail_embed)
    monkeypatch.setattr(ingestion.settings, "dashscope_api_key", "configured")

    result = await ingestion.ingest_paper(
        {
            "paper_id": "paper-1",
            "title": "A paper",
            "abstract": "A real abstract.",
        },
        chunk_repository=repository,
    )

    assert result.readable is True
    assert result.vector_indexed is False
    assert "EMBEDDING_FAILED" in result.warnings
    assert len(repository.saved) == 1


@pytest.mark.asyncio
async def test_existing_chroma_index_does_not_skip_missing_sqlite_chunks(monkeypatch) -> None:
    repository = FakeRepository()
    captured = {}

    async def no_pdf(_paper):
        return None

    async def embed(texts):
        captured["texts"] = texts
        return [[0.1] for _ in texts]

    monkeypatch.setattr(ingestion, "download_pdf", no_pdf)
    monkeypatch.setattr(ingestion, "embed_texts", embed)
    monkeypatch.setattr(ingestion.settings, "dashscope_api_key", "configured")
    monkeypatch.setattr(
        ingestion,
        "add_chunks",
        lambda chunks, embeddings, paper_id: captured.update({"chunks": chunks}),
    )

    result = await ingestion.ingest_paper(
        {"paper_id": "paper-1", "title": "A paper", "abstract": "Abstract"},
        chunk_repository=repository,
    )

    assert result.readable is True
    assert len(repository.saved) == 1
    assert captured["texts"]
