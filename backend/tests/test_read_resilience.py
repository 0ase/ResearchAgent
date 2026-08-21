import json
from types import SimpleNamespace

import pytest

import backend.agents.read as read_module
from backend.domain.errors import ResearchPipelineError
from backend.rag.ingestion import IngestionResult


class FakeRepository:
    def __init__(self, chunks_by_paper: dict[str, list[dict]] | None = None) -> None:
        self.chunks_by_paper = chunks_by_paper or {}

    async def list_for_paper(self, paper_id, _version):
        return self.chunks_by_paper.get(paper_id, [])


class FakeCompletions:
    async def create(self, **_kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            {
                                "paper_id": "ignored",
                                "summary": "Evidence-backed summary",
                                "claims": [],
                                "limitations": [],
                                "chunk_ids": [],
                            }
                        )
                    )
                )
            ]
        )


class FakeClient:
    def __init__(self, **_kwargs) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions())


def _state(papers: list[dict]) -> dict:
    return {
        "user_query": "比较两种方法",
        "output_language": "zh-CN",
        "selected_papers": papers,
    }


@pytest.mark.asyncio
async def test_read_uses_sqlite_chunks_without_embedding_key(monkeypatch) -> None:
    repository = FakeRepository(
        {
            "paper-1": [
                {
                    "paper_id": "paper-1",
                    "chunk_id": "chunk-1",
                    "content": "A durable abstract snapshot.",
                    "content_type": "abstract",
                }
            ]
        }
    )

    async def ingest(_paper, *, chunk_repository):
        assert chunk_repository is repository
        return IngestionResult(
            paper_id="paper-1",
            readable=True,
            warnings=["EMBEDDING_NOT_CONFIGURED"],
        )

    monkeypatch.setattr(read_module, "ChunkRepository", lambda: repository)
    monkeypatch.setattr(read_module, "ingest_paper", ingest)
    monkeypatch.setattr(read_module, "AsyncOpenAI", FakeClient)

    result = await read_module.read_papers(_state([{"paper_id": "paper-1"}]))

    assert result["paper_insights"][0]["answer"] == "Evidence-backed summary"
    assert result["final_answer"]
    assert "EMBEDDING_NOT_CONFIGURED" in result["warnings"]
    assert result["paper_claims"]


@pytest.mark.asyncio
async def test_all_unreadable_papers_return_structured_error(monkeypatch) -> None:
    async def ingest(paper, *, chunk_repository):
        return IngestionResult(
            paper_id=paper["paper_id"],
            readable=False,
            warnings=["PAPER_NO_READABLE_CONTENT"],
        )

    monkeypatch.setattr(read_module, "ChunkRepository", lambda: FakeRepository())
    monkeypatch.setattr(read_module, "ingest_paper", ingest)

    with pytest.raises(ResearchPipelineError) as exc_info:
        await read_module.read_papers(
            _state([{"paper_id": "paper-1"}, {"paper_id": "paper-2"}])
        )

    assert exc_info.value.code == "NO_READABLE_PAPERS"


@pytest.mark.asyncio
async def test_one_ingestion_failure_does_not_drop_other_papers(monkeypatch) -> None:
    repository = FakeRepository(
        {
            "paper-2": [
                {"chunk_id": "chunk-2", "paper_id": "paper-2", "content": "Second paper."}
            ]
        }
    )

    async def ingest(paper, *, chunk_repository):
        if paper["paper_id"] == "paper-1":
            raise RuntimeError("download failed")
        return IngestionResult(paper_id="paper-2", readable=True)

    monkeypatch.setattr(read_module, "ChunkRepository", lambda: repository)
    monkeypatch.setattr(read_module, "ingest_paper", ingest)
    monkeypatch.setattr(read_module, "AsyncOpenAI", FakeClient)

    result = await read_module.read_papers(
        _state([{"paper_id": "paper-1"}, {"paper_id": "paper-2"}])
    )

    assert [item["paper_id"] for item in result["paper_insights"]] == ["paper-2"]
    assert "PAPER_INGEST_FAILED" in result["warnings"]
    assert result["errors"] == []
