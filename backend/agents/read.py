import json
import re
import asyncio
from openai import AsyncOpenAI
from backend.agents.state import ResearchState
from backend.config import settings
from backend.rag.ingestion import ingest_paper
from backend.rag.vector_store import get_collection
from backend.rag.hybrid_search import hybrid_search


async def read_papers(state: ResearchState) -> dict:
    """Read Agent: ingest selected papers → search → per-paper LLM summaries"""

    selected = state.get("selected_papers", [])
    query = state.get("user_query", "")

    if not selected:
        return {"errors": ["no paper to read"], "paper_insights": []}

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
    tasks = [ingest_one(p) for p in selected]
    raw_ids = await asyncio.gather(*tasks, return_exceptions=True)
    ingested_ids = [rid for rid in raw_ids if isinstance(rid, str)]

    if not ingested_ids:
        return {"errors": ["no papers could be ingested"], "paper_insights": []}

    # 2. use paper_id to fetch all chunks of a paper from db
    collection = get_collection()
    paper_chunks = {}

    for pid in ingested_ids:
        try:
            data = collection.get(where={"paper_id": pid})
            docs = data.get("documents", [])
            if docs:
                paper_chunks[pid] = [
                    {"content": d, "chunk_index": i}
                    # for i, d in enumerate(docs[:10])
                    for i, d in enumerate(docs)
                ]
        except Exception as e:
            print(f"    [Read] fetch chunks failed for {pid}: {e}")

    if not paper_chunks:
        return {"paper_insights": []}

    client = AsyncOpenAI(
        api_key=settings.anthropic_api_key,
        base_url=settings.base_url,
        timeout=180.0,
        max_retries=2,
    )

    sem = asyncio.Semaphore(3)

    async def summarize_one(pid: str, chs: list[dict]) -> dict:
        chunks_text = "\n\n".join(
            # f"[Chunk {ci + 1}] {c['content'][:800]}" for ci, c in enumerate(chs)
            f"[Chunk {ci + 1}] {c['content']}" for ci, c in enumerate(chs)
        )
        prompt = (
            f"Question: {query}\n\n"
            f"Below are excerpts from a paper. "
            f"Summarize the paper's contribution to answer the question concisely. "
            f"Include specific methods, result, or claims.\n\n"
            f"{chunks_text}\n\n"
            "Return ONLY the summary, no JSON wrapper."
        )
        async with sem:
            resp = await client.chat.completions.create(
                model=settings.default_model,
                max_tokens=1500,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You read academic paper excerpts."
                            "Summarize the key points concisely, cite specific methods/results/claims."
                            "Respond in same language as the user's question."
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
    print(f"[Read] LLM summarized {len(per_paper)}/{len(tasks)} papers")



    return {
        "paper_insights": per_paper,
        "final_answer": "\n\n".join([
            f"**{ins['source']}**: {ins['answer']}"
            for ins in per_paper
        ]) if per_paper else "",
    }


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
