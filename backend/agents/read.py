import asyncio
import json
import re
from typing import Any

from openai import AsyncOpenAI

from backend.agents.state import ResearchState
from backend.config import settings
from backend.domain.evidence import CURRENT_INGESTION_VERSION, PaperChunk
from backend.domain.errors import ResearchPipelineError
from backend.rag.ingestion import IngestionResult, ingest_paper
from backend.repositories.chunk_repository import ChunkRepository
from backend.services.run_context import context_from_state
from backend.services.structured_output import (
    PaperClaim,
    PaperInsight,
    parse_model_output,
    validate_claims,
)


async def read_papers(state: ResearchState) -> dict:
    """Read papers from the durable SQLite evidence snapshot.

    Vector indexing is an optional acceleration layer. Reading therefore must
    continue from SQLite chunks when embeddings or Chroma are unavailable.
    """

    selected = state.get("selected_papers", [])
    query = state.get("user_query", "")
    output_language = state.get("output_language", "en")
    context = context_from_state(state)

    if not selected:
        raise ResearchPipelineError("NO_READABLE_PAPERS")

    repository = ChunkRepository()
    warnings: list[str] = []
    sem_ingest = asyncio.Semaphore(8)

    async def ingest_one(paper: dict) -> IngestionResult | None:
        async with sem_ingest:
            if context:
                context.raise_if_cancelled()
            paper_id = paper.get("paper_id") or paper.get("id") or paper.get("source_id", "unknown")
            try:
                result = await ingest_paper(paper, chunk_repository=repository)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                warnings.append("PAPER_INGEST_FAILED")
                print(f"    [Read] ingest failed for {paper_id}: {type(exc).__name__}")
                return None
            if context:
                context.raise_if_cancelled()
            if isinstance(result, IngestionResult):
                warnings.extend(result.warnings)
            elif result is True:
                # Keep compatibility with integrations that still return bool.
                result = IngestionResult(paper_id=paper_id, readable=True)
            else:
                result = IngestionResult(paper_id=paper_id, readable=False)
            if result.readable:
                print(f"    [Read] ingested: {paper_id}")
            return result

    raw_results = await asyncio.gather(
        *(ingest_one(paper) for paper in selected),
        return_exceptions=True,
    )
    ingested_results = [
        result
        for result in raw_results
        if isinstance(result, IngestionResult) and result.readable
    ]

    if not ingested_results:
        raise ResearchPipelineError("NO_READABLE_PAPERS")

    # SQLite is the canonical evidence store. Chroma is never required here.
    paper_chunks: dict[str, list[dict[str, Any]]] = {}
    for result in ingested_results:
        try:
            chunks = await _list_chunks(repository, result.paper_id)
            normalized_chunks = [
                _chunk_to_dict(chunk, paper_id=result.paper_id, index=index)
                for index, chunk in enumerate(chunks or [])
            ]
            if normalized_chunks:
                paper_chunks[result.paper_id] = normalized_chunks
            else:
                warnings.append("PAPER_CHUNKS_MISSING")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            warnings.append("PAPER_CHUNK_READ_FAILED")
            print(f"    [Read] fetch chunks failed for {result.paper_id}: {type(exc).__name__}")

    if not paper_chunks:
        raise ResearchPipelineError("NO_READABLE_PAPERS")

    try:
        client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.base_url,
            timeout=180.0,
            max_retries=2,
        )
    except Exception as exc:
        warnings.append("READ_MODEL_UNAVAILABLE")
        print(f"    [Read] model client unavailable: {type(exc).__name__}")
        return {
            "errors": ["NO_PAPER_INSIGHTS"],
            "warnings": warnings,
            "paper_insights": [],
        }

    sem = asyncio.Semaphore(3)

    async def summarize_one(pid: str, chs: list[dict[str, Any]]) -> dict:
        if context:
            context.raise_if_cancelled()
        chunks_text = "\n\n".join(
            f"[Chunk ID: {c['chunk_id']}] {c['content']}" for c in chs
        )
        prompt = (
            f"Question: {query}\n\n"
            f"Answer text in {output_language}. Below are excerpts from one paper. "
            f"Return a JSON object with exactly these keys: paper_id, summary, claims, "
            f"limitations and chunk_ids. Each direct claim must cite an existing Chunk ID "
            f"and include an exact evidence_text.\n\n"
            f"{chunks_text}\n\n"
            'Return ONLY valid JSON, for example: '
            '{"paper_id":"...","summary":"...","claims":[],"limitations":[],"chunk_ids":[]}'
        )
        async with sem:
            resp = await client.chat.completions.create(
                model=settings.default_model,
                max_tokens=1500,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You read academic paper excerpts. "
                            "Return only a valid JSON object using English field names. "
                            "Keep paper metadata and evidence excerpts exactly as sourced."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
        if context:
            context.raise_if_cancelled()
        raw_text = resp.choices[0].message.content.strip()
        insight = parse_model_output(raw_text, PaperInsight, fallback_paper_id=pid)
        if insight is None:
            insight = PaperInsight(paper_id=pid, summary=raw_text)
        insight = insight.model_copy(update={"paper_id": pid})
        claims = validate_claims(
            insight.claims,
            {chunk["chunk_id"]: chunk for chunk in chs},
        )
        if not claims:
            claims = _fallback_claim(pid, chs)
        insight = insight.model_copy(
            update={
                "claims": claims,
                "chunk_ids": [chunk["chunk_id"] for chunk in chs],
            }
        )
        summary = insight.summary
        print(f"    [Read] {pid}: {len(summary)} chars, {len(claims)} claims")
        return {
            "query": query,
            "answer": summary,
            "source": pid,
            "sources": [pid],
            "paper_id": pid,
            "claims": [claim.model_dump() for claim in claims],
            "limitations": insight.limitations,
            "chunk_ids": insight.chunk_ids,
        }

    raw_summary_results = await asyncio.gather(
        *(summarize_one(pid, chunks) for pid, chunks in paper_chunks.items()),
        return_exceptions=True,
    )
    per_paper = []
    for result in raw_summary_results:
        if isinstance(result, dict):
            per_paper.append(result)
        elif isinstance(result, asyncio.CancelledError):
            raise result
        else:
            warnings.append("READ_SUMMARY_FAILED")
    print(f"[Read] LLM summarized {len(per_paper)}/{len(paper_chunks)} papers")

    return {
        "errors": [] if per_paper else ["NO_PAPER_INSIGHTS"],
        "warnings": warnings,
        "paper_insights": per_paper,
        "paper_claims": [claim for insight in per_paper for claim in insight.get("claims", [])],
        "chunks": [
            chunk
            for chunks in paper_chunks.values()
            for chunk in chunks
        ],
        "final_answer": "\n\n".join(
            f"**{ins['source']}**: {ins['answer']}" for ins in per_paper
        ) if per_paper else "",
    }


async def _list_chunks(repository: ChunkRepository, paper_id: str) -> list[PaperChunk | dict]:
    """Load current chunks while tolerating small integration repositories."""
    try:
        return await repository.list_for_paper(paper_id, CURRENT_INGESTION_VERSION)
    except TypeError:
        return await repository.list_for_paper(paper_id)


def _chunk_to_dict(chunk: PaperChunk | dict, *, paper_id: str, index: int) -> dict[str, Any]:
    if isinstance(chunk, PaperChunk):
        value = chunk.model_dump()
    elif hasattr(chunk, "model_dump"):
        value = chunk.model_dump()
    else:
        value = dict(chunk)
    return {
        **value,
        "paper_id": value.get("paper_id") or paper_id,
        "content": str(value.get("content") or "").strip(),
        "chunk_index": value.get("chunk_index", index),
        "chunk_id": value.get("chunk_id") or f"{paper_id}:chunk:{index}",
        "page_start": value.get("page_start"),
        "page_end": value.get("page_end"),
        "content_type": value.get("content_type", "pdf"),
    }


def _fallback_claim(paper_id: str, chunks: list[dict[str, Any]]) -> list[PaperClaim]:
    """Create one directly verifiable claim when a model omits claim objects."""
    for chunk in chunks:
        evidence_text = str(chunk.get("content") or "").strip()
        if not evidence_text:
            continue
        excerpt = evidence_text[:500]
        return [
            PaperClaim(
                claim_id=f"{paper_id}:claim:summary",
                paper_id=paper_id,
                statement=excerpt,
                support_type="direct",
                chunk_ids=[str(chunk["chunk_id"])],
                evidence_text=excerpt,
            )
        ]
    return []


def _parse_paper_summaries(text: str, paper_index: dict, query: str) -> list[dict]:
    """Parse LLM's JSON into per-paper insights. Tolerant of truncated JSON."""
    text = text.strip()
    data = None

    # 尝试 1：直接解析
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试 2：提取 ```json ... ``` 代码块
    if data is None:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

    # 尝试 3：正则找 {...}，补全可能被截断的 JSON
    if data is None:
        match = re.search(r"\{.*\"papers\"\s*:\s*\[.*\]", text, re.DOTALL)
        if match:
            raw = match.group(0)
            # 补全截断：如果最后不是 } 或 ]，尝试补上
            if not raw.rstrip().endswith("}"):
                raw = raw.rstrip().rstrip(",") + "]}"
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                pass

    # 兜底
    if data is None:
        data = {}

    results = []
    for item in data.get("papers", []):
        num = str(item.get("paper_num", ""))
        source_id = paper_index.get(num, f"paper_{num}")
        summary = item.get("summary", "")
        # 标记截断
        if summary and not summary.rstrip().endswith((".", "。", ")", "]")):
            summary += "... [truncated]"
        results.append({
            "query": query,
            "answer": summary,
            "source": source_id,
            "sources": [source_id],
        })
    return results
