import asyncio
import time
from types import SimpleNamespace

import httpx
import pytest

from backend.agents import read
from backend.rag.ingestion import IngestionResult
from backend.services import paper_cache, blocking_worker
from backend.services.run_context import ResearchRunContext


@pytest.mark.asyncio
async def test_slow_paper_does_not_drop_completed_evidence(monkeypatch):
    async def ingest(paper, **kwargs):
        if paper["paper_id"] == "slow":
            await asyncio.sleep(60)
        return IngestionResult(paper_id=paper["paper_id"], readable=True)
    class Repo:
        async def list_for_paper(self, pid, *_):
            return [{"chunk_id": pid + "-chunk", "paper_id": pid, "content": "Actual source evidence."}]
    monkeypatch.setattr(read, "ingest_paper", ingest)
    monkeypatch.setattr(read, "ChunkRepository", Repo)
    monkeypatch.setattr(read.settings, "read_paper_timeout", 0.05)
    monkeypatch.setattr(read.settings, "read_stage_timeout", 1)
    events = []
    class Recorder:
        async def append(self, **kwargs): events.append(kwargs)
    context = ResearchRunContext("t", Recorder(), asyncio.Event())
    started = time.monotonic()
    result = await read.read_papers({"selected_papers": [{"paper_id": "good"}, {"paper_id": "slow"}], "_run_context": context})
    assert time.monotonic() - started < 2
    assert [i["paper_id"] for i in result["paper_insights"]] == ["good"]
    assert "READ_PAPER_TIMEOUT" in result["warnings"]
    assert events[-1]["payload"]["completed"] == 2
    assert events[-1]["payload"]["degraded"] == 1
    assert events[-1]["payload"]["failed"] == 1


@pytest.mark.asyncio
async def test_stage_deadline_retains_chunks_when_model_stalls(monkeypatch):
    async def ingest(paper, **kwargs): return IngestionResult(paper_id="p", readable=True)
    class Repo:
        async def list_for_paper(self, *_): return [{"chunk_id": "c", "paper_id": "p", "content": "Traceable source."}]
    async def create(**kwargs): await asyncio.sleep(60)
    monkeypatch.setattr(read, "ingest_paper", ingest)
    monkeypatch.setattr(read, "ChunkRepository", Repo)
    monkeypatch.setattr(read, "AsyncOpenAI", lambda **kw: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    monkeypatch.setattr(read.settings, "read_stage_timeout", 0.05)
    result = await read.read_papers({"selected_papers": [{"paper_id": "p"}]})
    assert result["paper_insights"][0]["claims"][0]["evidence_text"] == "Traceable source."
    assert "READ_STAGE_TIMEOUT" in result["warnings"]


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True])
async def test_blocking_worker_is_reaped_on_timeout_or_cancel(monkeypatch, tmp_path, cancel):
    original = asyncio.create_subprocess_exec
    processes = []
    async def slow_process(*args, **kwargs):
        pid_file = tmp_path / "worker.pid"
        program = "import os,sys,time; from pathlib import Path; Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)"
        process = await original(args[0], "-c", program, str(pid_file), **kwargs)
        async with asyncio.timeout(5):
            while not pid_file.exists():
                await asyncio.sleep(0.01)
        assert int(pid_file.read_text()) == process.pid, "Termination must target the interpreter, not a venv redirector"
        processes.append(process)
        return process
    monkeypatch.setattr(asyncio, "create_subprocess_exec", slow_process)
    task = asyncio.create_task(blocking_worker.run_blocking_worker("pdf", {}, 0.05 if not cancel else 60))
    if cancel:
        while not processes: await asyncio.sleep(0.01)
        task.cancel()
    with pytest.raises(asyncio.CancelledError if cancel else TimeoutError):
        await task
    assert processes[0].returncode is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("oversize", [False, True])
async def test_download_stream_limits_and_cleans_partial(monkeypatch, tmp_path, oversize):
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"%PDF" + b"x" * 65532
            if not oversize: await asyncio.sleep(60)
            yield b"x" * 65536
    original = httpx.AsyncClient
    monkeypatch.setattr(paper_cache.httpx, "AsyncClient", lambda **kwargs: original(**kwargs,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=Stream()))))
    monkeypatch.setattr(paper_cache.settings, "paper_cache_dir", str(tmp_path))
    monkeypatch.setattr(paper_cache.settings, "download_timeout", 0.05)
    monkeypatch.setattr(paper_cache, "MAX_PDF_BYTES", 65536)
    assert await paper_cache.download_pdf({"pdf_url": "https://example.test/paper.pdf"}) is None
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_real_pdf_worker_returns_traceable_chunks(tmp_path):
    import fitz
    path = tmp_path / "paper.pdf"
    with fitz.open() as doc:
        doc.new_page().insert_text((72, 72), "Source evidence from a real PDF.")
        doc.save(path)
    chunks = await blocking_worker.run_blocking_worker("pdf", {"path": str(path), "paper_id": "p",
        "chunk_size": 512, "chunk_overlap": 128}, 10)
    assert chunks[0]["page_start"] == 1
    assert "Source evidence" in chunks[0]["content"]
