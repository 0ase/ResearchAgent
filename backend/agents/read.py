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
    parse_paper_insight_output,
    validate_claims,
)


def _merge_paper_insights(
    selected_papers: list[dict],
    existing_insights: list[dict],
    new_insights: list[dict],
    limit: int,
) -> list[dict]:
    """Retain existing evidence; ranking only orders the admitted insights."""
    by_source: dict[str, dict] = {}
    for insight in existing_insights + new_insights:
        source = str(insight.get("paper_id") or insight.get("source") or "").strip()
        if source and source not in by_source and len(by_source) < limit:
            by_source[source] = insight
    ranked_ids = [str(p.get("paper_id") or p.get("source_id") or "").strip()
                  for p in selected_papers]
    order = dict.fromkeys(ranked_ids + list(by_source))
    return [by_source[source] for source in order if source in by_source]


async def read_papers(state: ResearchState) -> dict:
    """Complete papers independently; all waits share the read deadline."""
    from backend.api.schemas.tasks import ResearchStage
    from backend.rag.ingestion import index_paper_chunks
    from backend.services.provider_retry import request_with_retry

    limit = min(state.get("max_papers", 15), 15)
    selected = state.get("selected_papers", [])
    existing = _merge_paper_insights([], state.get("paper_insights", []), [], limit)
    prior_ids = {item.get("paper_id") or item.get("source") for item in existing}
    remaining_budget = max(0, limit - len(prior_ids))
    pending = []
    admitted = set(prior_ids)
    for paper in selected:
        pid = paper.get("paper_id") or paper.get("source_id") or paper.get("id")
        if pid and pid not in admitted and len(pending) < remaining_budget:
            pending.append(paper)
            admitted.add(pid)
    context = context_from_state(state)
    if not selected and not existing:
        raise ResearchPipelineError("NO_READABLE_PAPERS")
    repository = ChunkRepository()
    warnings = []
    outcomes = {}
    paper_chunks = {}
    counts = {"total": len(pending), "completed": 0, "succeeded": 0, "degraded": 0, "failed": 0}
    semaphore = asyncio.Semaphore(settings.read_concurrency)
    parse_semaphore = asyncio.Semaphore(settings.pdf_parse_concurrency)
    vector_semaphore = asyncio.Semaphore(1)
    vector_disabled = False
    stage_expired = False
    client = None
    try:
        if pending:
            client = AsyncOpenAI(api_key=settings.deepseek_api_key, base_url=settings.base_url,
                                 timeout=min(30, settings.read_summary_timeout), max_retries=0)
    except Exception:
        warnings.append("READ_MODEL_UNAVAILABLE")

    def check_cancelled():
        if context:
            context.raise_if_cancelled()

    def fallback(pid, chunks):
        warnings.append("READ_STRUCTURED_OUTPUT_DEGRADED")
        return {"query": state.get("user_query", ""), "answer": chunks[0]["content"][:1500],
                "source": pid, "sources": [pid], "paper_id": pid,
                "claims": [c.model_dump() for c in _fallback_claim(pid, chunks)],
                "limitations": ["Deterministic excerpt; model summary unavailable"],
                "chunk_ids": [c["chunk_id"] for c in chunks]}

    async def summarize(pid, chunks, local_warnings):
        if client is None:
            raise RuntimeError("READ_MODEL_UNAVAILABLE")
        excerpts = "\n\n".join(f"[Chunk ID: {c['chunk_id']}] {c['content']}" for c in chunks)
        prompt = (f"Question: {state.get('user_query', '')}\n"
                  f"Reading objective: {state.get('current_task', '')}\n"
                  f"Answer text in {state.get('output_language', 'en')}. "
                  f"Canonical paper ID: {pid}. Allowed Chunk IDs: {[c['chunk_id'] for c in chunks]}. "
                  f"Return JSON matching this schema: {json.dumps(PaperInsight.model_json_schema())}. "
                  "Claims use claim_id, paper_id, statement, support_type, chunk_ids, evidence_text. "
                  "Each direct claim must cite an allowed Chunk ID; evidence_text must be a contiguous verbatim substring of that chunk.\n" + excerpts)
        async with asyncio.timeout(settings.read_summary_timeout):
            response = await request_with_retry(lambda: client.chat.completions.create(
                model=settings.light_model or settings.default_model, max_tokens=1500,
                messages=[{"role": "system", "content": "Read academic excerpts. Return only JSON using English field names; preserve source metadata and evidence."},
                          {"role": "user", "content": prompt}]))
        text = (response.choices[0].message.content or "").strip()
        if not text:
            raise ValueError("Empty summary")
        insight, degraded = parse_paper_insight_output(text, canonical_paper_id=pid)
        claims = validate_claims(insight.claims, {c["chunk_id"]: c for c in chunks})
        if not claims or all(c.support_type == "unverified" for c in claims):
            claims = _fallback_claim(pid, chunks)
            degraded = True
        if degraded:
            local_warnings.append("READ_STRUCTURED_OUTPUT_DEGRADED")
        if not insight.summary:
            insight.summary = chunks[0]["content"][:1500]
        return {"query": state.get("user_query", ""), "answer": insight.summary,
                "source": pid, "sources": [pid], "paper_id": pid,
                "claims": [c.model_dump() for c in claims], "limitations": insight.limitations,
                "chunk_ids": [c["chunk_id"] for c in chunks]}

    async def process(paper):
        nonlocal vector_disabled
        pid = str(paper.get("paper_id") or paper.get("source_id") or paper.get("id") or "unknown")
        local_warnings = []
        async with semaphore:
            check_cancelled()
            try:
                async with asyncio.timeout(settings.read_paper_timeout):
                    ingested = await ingest_paper(paper, chunk_repository=repository,
                                                   index_vectors=False, parse_semaphore=parse_semaphore)
                    check_cancelled()
                    if isinstance(ingested, IngestionResult):
                        local_warnings.extend(ingested.warnings)
                        warnings.extend(ingested.warnings)
                    chunks = await _list_chunks(repository, pid)
                    chunks = [_chunk_to_dict(c, paper_id=pid, index=i) for i, c in enumerate(chunks or [])]
                    chunks = [c for c in chunks if c["content"].strip()]
                    if not chunks:
                        raise ValueError("No readable chunks")
                    terms = set(re.findall(r"\w+", state.get("user_query", "").lower()))
                    chunks.sort(key=lambda c: len(terms & set(re.findall(r"\w+", c["content"].lower()))), reverse=True)
                    # Keep all canonical chunks for indexing; only summaries use top-k.
                    paper_chunks[pid] = chunks
                    excerpts = chunks[:settings.retrieval_top_k]
                    try:
                        outcomes[pid] = await summarize(pid, excerpts, local_warnings)
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        local_warnings.append("READ_SUMMARY_FALLBACK")
                        outcomes[pid] = fallback(pid, excerpts)
                    check_cancelled()
                    async with vector_semaphore:
                        if vector_disabled:
                            local_warnings.append("EMBEDDING_FAILED")
                        else:
                            index_warnings = await index_paper_chunks(pid, chunks)
                            local_warnings.extend(index_warnings)
                            if "EMBEDDING_FAILED" in index_warnings:
                                vector_disabled = True
            except asyncio.CancelledError:
                raise
            except TimeoutError:
                local_warnings.append("READ_PAPER_TIMEOUT")
                if pid in paper_chunks and pid not in outcomes:
                    outcomes[pid] = fallback(pid, paper_chunks[pid][:settings.retrieval_top_k])
            except Exception:
                local_warnings.append("PAPER_INGEST_FAILED")
            check_cancelled()
            warnings.extend(local_warnings)
            counts["completed"] += 1
            counts["failed" if pid not in outcomes else "degraded" if local_warnings else "succeeded"] += 1
            if context:
                await context.stage_progress(ResearchStage.READ, {
                    "attempt": context.attempts.get("read", 1), **counts,
                    "metrics": {"papersRead": len(existing) + len(outcomes)},
                })

    jobs = [asyncio.create_task(process(paper)) for paper in pending]
    try:
        if jobs:
            _, unfinished = await asyncio.wait(jobs, timeout=settings.read_stage_timeout)
            if unfinished:
                stage_expired = True
                warnings.append("READ_STAGE_TIMEOUT")
                for job in unfinished:
                    job.cancel()
            results = await asyncio.gather(*jobs, return_exceptions=True)
            for result in results:
                if isinstance(result, asyncio.CancelledError) and not stage_expired:
                    raise result
                if isinstance(result, Exception):
                    raise result
        check_cancelled()
    finally:
        for job in jobs:
            if not job.done():
                job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)
        if client is not None and hasattr(client, "close"):
            await client.close()
    if stage_expired:
        for pid, values in paper_chunks.items():
            if pid not in outcomes:
                outcomes[pid] = fallback(pid, values[:settings.retrieval_top_k])
                warnings.append("READ_SUMMARY_FALLBACK")
        remaining = counts["total"] - counts["completed"]
        retained_unfinished = max(0, len(outcomes) - counts["succeeded"] - counts["degraded"])
        counts["completed"] = counts["total"]
        counts["degraded"] += retained_unfinished
        counts["failed"] += remaining - retained_unfinished
        if context:
            await context.stage_progress(ResearchStage.READ, {"attempt": context.attempts.get("read", 1), **counts,
                "metrics": {"papersRead": len(existing) + len(outcomes)}})
    insights = _merge_paper_insights(selected, existing, list(outcomes.values()), limit)
    if not insights:
        raise ResearchPipelineError("NO_READABLE_PAPERS")
    retained = {i["source"] for i in insights}
    chunks = [c for c in state.get("chunks", []) if c.get("paper_id") in retained and c.get("paper_id") not in paper_chunks]
    chunks.extend(c for pid, values in paper_chunks.items() if pid in retained for c in values)
    return {"errors": [], "warnings": list(dict.fromkeys(warnings)), "paper_insights": insights,
            "paper_claims": [claim for insight in insights for claim in insight.get("claims", [])],
            "chunks": chunks, "final_answer": "\n\n".join(f"**{i['source']}**: {i['answer']}" for i in insights)}


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
