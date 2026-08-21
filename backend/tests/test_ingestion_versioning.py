import pytest

import backend.rag.ingestion as ingestion
from backend.config import Settings
from backend.db.connection import open_database
from backend.db.migrate import migrate_database
from backend.domain.evidence import CURRENT_INGESTION_VERSION
from backend.repositories.chunk_repository import ChunkRepository


class FakeChunkRepository:
    def __init__(self, existing=None) -> None:
        self.existing = existing or []
        self.saved = []

    async def list_for_paper(self, _paper_id, _version):
        return self.existing

    async def upsert_chunks(self, paper_id, chunks):
        self.saved.append((paper_id, chunks))


@pytest.mark.asyncio
async def test_abstract_fallback_is_saved_with_abstract_content_type(monkeypatch) -> None:
    repository = FakeChunkRepository()
    captured = {}

    async def no_pdf(_paper):
        return None

    async def embed(texts):
        captured["texts"] = texts
        return [[0.1, 0.2]]

    monkeypatch.setattr(ingestion, "download_pdf", no_pdf)
    monkeypatch.setattr(ingestion, "embed_texts", embed)
    monkeypatch.setattr(ingestion.settings, "dashscope_api_key", "configured")
    monkeypatch.setattr(ingestion, "add_chunks", lambda chunks, embeddings, paper_id: captured.update({"chunks": chunks}))

    result = await ingestion.ingest_paper(
        {
            "paper_id": "paper-1",
            "title": "Fallback paper",
            "abstract": "A useful abstract.",
        },
        chunk_repository=repository,
    )

    assert result.readable is True
    saved_chunks = repository.saved[0][1]
    assert saved_chunks[0]["content_type"] == "abstract"
    assert saved_chunks[0]["page_start"] is None
    assert saved_chunks[0]["ingestion_version"] == CURRENT_INGESTION_VERSION
    assert captured["texts"] == [saved_chunks[0]["content"]]


@pytest.mark.asyncio
async def test_current_ingestion_version_skips_embedding(monkeypatch) -> None:
    async def fail_embed(_texts):
        raise AssertionError("embedding should not run for current chunks")

    monkeypatch.setattr(ingestion, "embed_texts", fail_embed)

    result = await ingestion.ingest_paper(
        {"paper_id": "paper-1"},
        chunk_repository=FakeChunkRepository(existing=[{"chunk_id": "chunk-1"}]),
    )
    assert result.readable is True
    assert result.chunk_count == 1


@pytest.mark.asyncio
async def test_old_version_is_reingested_with_current_version(monkeypatch) -> None:
    repository = FakeChunkRepository()
    captured = {}

    async def no_pdf(_paper):
        return None

    monkeypatch.setattr(ingestion, "download_pdf", no_pdf)
    monkeypatch.setattr(ingestion, "embed_texts", lambda texts: _embeddings(texts))
    monkeypatch.setattr(ingestion.settings, "dashscope_api_key", "configured")
    monkeypatch.setattr(ingestion, "add_chunks", lambda chunks, embeddings, paper_id: captured.update({"chunks": chunks}))

    result = await ingestion.ingest_paper(
        {"paper_id": "paper-1", "title": "Old version", "abstract": "Abstract"},
        chunk_repository=repository,
    )
    assert result.readable is True
    assert captured["chunks"][0]["ingestion_version"] == CURRENT_INGESTION_VERSION
    assert len(repository.saved) == 1


@pytest.mark.asyncio
async def test_sqlite_chunk_repository_keeps_evidence_snapshot(tmp_path) -> None:
    settings = Settings(_env_file=None, database_path=str(tmp_path / "research.db"))
    await migrate_database(settings)
    repository = ChunkRepository(lambda: open_database(settings))
    chunk = {
        "chunk_id": "chunk:1",
        "paper_id": "paper-1",
        "content": "Evidence text",
        "content_hash": "hash-1",
        "chunk_index": 0,
        "total_chunks": 1,
        "page_start": 3,
        "page_end": 4,
        "content_type": "pdf",
        "ingestion_version": CURRENT_INGESTION_VERSION,
    }

    await repository.upsert_chunks("paper-1", [chunk])
    loaded = await repository.list_for_paper("paper-1", CURRENT_INGESTION_VERSION)

    assert loaded[0].chunk_id == "chunk:1"
    assert loaded[0].content == "Evidence text"
    assert (loaded[0].page_start, loaded[0].page_end) == (3, 4)


async def _embeddings(texts):
    return [[0.1] for _ in texts]
