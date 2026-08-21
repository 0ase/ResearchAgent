import json
import re
import asyncio
from openai import AsyncOpenAI
from backend.agents.state import ResearchState
from backend.config import settings
from backend.rag.ingestion import ingest_paper
from backend.rag.embeddings import embed_single
from backend.rag.vector_store import get_collection


def _merge_paper_insights(
    selected_papers: list[dict],
    existing_insights: list[dict],
    new_insights: list[dict],
    limit: int,
) -> list[dict]:
    """Merge reading rounds without duplicates, following current paper ranking."""
    by_source: dict[str, dict] = {}
    for insight in existing_insights + new_insights:
        source = str(insight.get("source") or "").strip()
        if source:
            by_source[source] = insight

    merged: list[dict] = []
    used_sources: set[str] = set()

    # Current Filter ranking decides which evidence is retained after a new search.
    for paper in selected_papers:
        source = str(paper.get("source_id") or "").strip()
        insight = by_source.get(source)
        if insight is not None and source not in used_sources:
            merged.append(insight)
            used_sources.add(source)
        if len(merged) >= limit:
            return merged

    # If a newly selected paper failed to parse, retain older valid evidence rather
    # than silently shrinking the evidence pool.
    for insight in existing_insights + new_insights:
        source = str(insight.get("source") or "").strip()
        if source and source not in used_sources:
            merged.append(insight)
            used_sources.add(source)
        if len(merged) >= limit:
            break

    return merged


async def read_papers(state: ResearchState) -> dict:
    """Read Agent: ingest selected papers → search → per-paper LLM summaries"""
    max_papers_to_read = min(state.get("max_papers", 15), 15)
    selected = state.get("selected_papers", [])[:max_papers_to_read]
    existing_insights = state.get("paper_insights", [])
    existing_sources = {
        str(insight.get("source") or "").strip()
        for insight in existing_insights
        if insight.get("source")
    }
    papers_to_read = [
        paper
        for paper in selected
        if str(paper.get("source_id") or "").strip() not in existing_sources
    ]
    query = state.get("user_query", "").strip()
    objective = state.get("current_task", "").strip()

    if not selected:
        return {
            "errors": ["no paper to read"],
            "paper_insights": existing_insights[:max_papers_to_read],
        }

    if not papers_to_read:
        return {
            "paper_insights": _merge_paper_insights(
                selected,
                existing_insights,
                [],
                max_papers_to_read,
            )
        }

    # 1. put the most relevant paper into db
    # ingested_ids = []
    # for paper in selected:
    #     paper_id = paper.get("source_id", "unknown")
    #     success = await ingest_paper(paper)
    #     if success:
    #         ingested_ids.append(paper_id)
    #         print(f"    [Read] ingested: {paper_id}")

    # if not ingested_ids:
    #     return {"errors": ["no papers could be ingested"], "paper_insights": []}

    sem_ingest = asyncio.Semaphore(8)
    async def ingest_one(paper: dict) -> str | None:
        async with sem_ingest:
            paper_id = paper.get("source_id", "unknown")
            success = await ingest_paper(paper)
            if success:
                print(f"    [Read] ingested: {paper_id}")
                return paper_id
            return None
    # 1. put the most relevant paper into db
    tasks = [ingest_one(p) for p in papers_to_read]
    raw_ids = await asyncio.gather(*tasks, return_exceptions=True)
    ingested_ids = [rid for rid in raw_ids if isinstance(rid, str)]

    if not ingested_ids:
        return {
            "errors": ["no new papers could be ingested"],
            "paper_insights": _merge_paper_insights(
                selected,
                existing_insights,
                [],
                max_papers_to_read,
            ),
        }

    # 2. 每篇论文只读取与原始问题最相关的若干切片，避免把整篇 PDF
    # 全部塞进模型上下文。
    collection = get_collection()
    paper_chunks = {}
    try:
        query_embedding = await embed_single(query)
    except Exception as exc:
        print(f"    [Read] query embedding failed, falling back to first chunks: {exc}")
        query_embedding = None

    for pid in ingested_ids:
        try:
            data = collection.get(where={"paper_id": pid})
            docs = data.get("documents") or []
            if docs:
                top_k = min(settings.retrieval_top_k, len(docs))
                relevant_docs = docs[:top_k]

                if query_embedding is not None:
                    result = collection.query(
                        query_embeddings=[query_embedding],
                        where={"paper_id": pid},
                        n_results=top_k,
                        include=["documents", "metadatas"],
                    )
                    queried_docs = (result.get("documents") or [[]])[0]
                    if queried_docs:
                        relevant_docs = queried_docs

                paper_chunks[pid] = [
                    {"content": document, "chunk_index": index}
                    for index, document in enumerate(relevant_docs)
                ]
        except Exception as e:
            print(f"    [Read] fetch chunks failed for {pid}: {e}")

    if not paper_chunks:
        return {
            "errors": ["no readable chunks found for newly selected papers"],
            "paper_insights": _merge_paper_insights(
                selected,
                existing_insights,
                [],
                max_papers_to_read,
            ),
        }

    client = AsyncOpenAI(
        api_key=settings.anthropic_api_key,
        base_url=settings.base_url,
        timeout=180.0,
        max_retries=2,
    )

    # Fifteen papers would otherwise require five serial LLM waves. Five concurrent
    # summaries keep the larger evidence target practical without unbounded fan-out.
    sem = asyncio.Semaphore(settings.read_concurrency)

    async def summarize_one(pid: str, chs: list[dict]) -> dict:
        chunks_text = "\n\n".join(
            # f"[Chunk {ci + 1}] {c['content'][:800]}" for ci, c in enumerate(chs)
            f"[Chunk {ci + 1}] {c['content']}" for ci, c in enumerate(chs)
        )
        prompt = (
            f"Question: {query}\n\n"
            f"Current reading objective: {objective or 'Extract evidence relevant to the question.'}\n\n"
            f"Below are excerpts from a paper. "
            f"Summarize the paper's contribution to answer the question concisely. "
            f"Include specific methods, result, or claims.\n\n"
            f"{chunks_text}\n\n"
            "Return ONLY the summary, no JSON wrapper."
        )
        async with sem:
            resp = await client.chat.completions.create(
                model=settings.light_model or settings.default_model,
                max_tokens=1000,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You read academic paper excerpts. "
                            "Summarize the key points concisely and cite specific "
                            "methods, results, or claims. "
                            "Respond in the same language as the user's question. "
                            "Return plain text only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ]
            )
        summary = resp.choices[0].message.content.strip()
        print(f"    [Read] {pid}: {len(summary)} chars")
        return {
            "query": query,
            "answer": summary,
            "source": pid,
            "sources": [pid],
        }

    tasks = [summarize_one(pid, chs) for pid, chs in paper_chunks.items()]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)
    per_paper = [r for r in raw_results if isinstance(r, dict)]
    summary_errors = [
        f"paper summary failed: {type(result).__name__}: {result}"
        for result in raw_results
        if isinstance(result, Exception)
    ]
    print(f"[Read] LLM summarized {len(per_paper)}/{len(tasks)} papers")



    merged_insights = _merge_paper_insights(
        selected,
        existing_insights,
        per_paper,
        max_papers_to_read,
    )
    update = {
        "paper_insights": merged_insights,
        "final_answer": "\n\n".join([
            f"**{ins['source']}**: {ins['answer']}"
            for ins in merged_insights
        ]) if merged_insights else "",
    }
    if summary_errors:
        update["errors"] = summary_errors
    return update


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
