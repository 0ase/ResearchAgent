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

    async def ingest(_paper, *, chunk_repository, **kwargs):
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
    async def ingest(paper, *, chunk_repository, **kwargs):
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

    async def ingest(paper, *, chunk_repository, **kwargs):
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


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ['{"unknown":1}', '{"summary":"truncated', 'plain summary'])
async def test_read_structured_degradation_is_explicit(monkeypatch, text):
    async def create(**kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])
    async def ingest(*args, **kwargs):
        return IngestionResult(paper_id="p", readable=True)
    monkeypatch.setattr(read_module, "AsyncOpenAI", lambda **kwargs: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    monkeypatch.setattr(read_module, "ingest_paper", ingest)
    monkeypatch.setattr(read_module, "ChunkRepository", lambda: FakeRepository({
        "p": [{"paper_id": "p", "chunk_id": "c", "content": "Actual source excerpt."}]}))
    result = await read_module.read_papers(_state([{"paper_id": "p"}]))
    assert "READ_STRUCTURED_OUTPUT_DEGRADED" in result["warnings"]
    assert not result["paper_insights"][0]["answer"].startswith(("{", "["))
    assert result["paper_claims"][0]["paper_id"] == "p"


@pytest.mark.asyncio
@pytest.mark.parametrize("old_ids,mode", [(["old"], "ok"), (["old", "old"], "ok"),
    (["old", "older", "oldest"], "ok"), (["old"], "failure"), (["old"], "timeout")])
async def test_cross_round_total_budget_retains_old_evidence(monkeypatch, old_ids, mode):
    import asyncio
    from backend.services.run_context import ResearchRunContext
    calls, events = [], []
    class Recorder:
        async def append(self, **kwargs): events.append(kwargs)
    async def ingest(paper, **kwargs):
        calls.append(paper["paper_id"])
        if mode == "failure": raise RuntimeError("injected")
        if mode == "timeout": await asyncio.sleep(60)
        return IngestionResult(paper_id=paper["paper_id"], readable=True)
    monkeypatch.setattr(read_module, "ingest_paper", ingest)
    monkeypatch.setattr(read_module, "AsyncOpenAI", FakeClient)
    monkeypatch.setattr(read_module.settings, "read_paper_timeout", 0.03)
    monkeypatch.setattr(read_module, "ChunkRepository", lambda: FakeRepository({
        p: [{"paper_id": p, "chunk_id": p+"-c", "content": "Actual evidence."}] for p in ("a", "b", "c")}))
    state = {**_state([{"paper_id": p} for p in ("a", "b", "c")]), "max_papers": 3,
        "paper_insights": [{"source": p, "paper_id": p, "answer": "Old evidence", "claims": []} for p in old_ids],
        "_run_context": ResearchRunContext("t", Recorder(), asyncio.Event())}
    result = await read_module.read_papers(state)
    assert len(calls) == 3-len(set(old_ids))
    ids = {i["source"] for i in result["paper_insights"]}
    assert set(old_ids) <= ids
    assert len(ids) <= 3
    metrics = [len(set(old_ids))]+[e["payload"]["metrics"]["papersRead"] for e in events]
    assert metrics == sorted(metrics) and max(metrics) <= 3
    assert len(ids) == (3 if mode == "ok" else len(set(old_ids)))
