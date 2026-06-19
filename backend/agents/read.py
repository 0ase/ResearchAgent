import json
import re
from openai import AsyncOpenAI
from backend.agents.state import ResearchState
from backend.config import settings
from backend.rag.ingestion import ingest_paper
from backend.rag.hybrid_search import hybrid_search
from backend.rag.vector_store import is_paper_indexed


async def read_papers(state: ResearchState) -> dict:
    """Read Agent: ingest papers → search → per-paper LLM summaries"""

    papers = state.get("raw_papers", [])
    query = state.get("user_query", "")

    if not papers:
        return {"errors": ["no paper to read"], "paper_insights": []}

    # 1. 入库最多 20 篇"可能相关"的论文
    query_words = set(query.lower().split())
    ingested_ids = []
    tried = 0
    for paper in papers:
        if len(ingested_ids) >= 20:
            break
        tried += 1
        if not paper.get("pdf_url"):
            continue
        title_words = set(paper.get("title", "").lower().split())
        abstract_words = set(paper.get("abstract", "").lower().split())
        overlap = query_words & (title_words | abstract_words)
        if not overlap and tried <= 40:
            continue  # 不相关的跳过，但前 20 篇后的全收（防止全跳过）
        paper_id = paper.get("source_id", "unknown")
        was_indexed = is_paper_indexed(paper_id)
        success = await ingest_paper(paper)
        if success:
            ingested_ids.append(paper_id)
            label = "缓存" if was_indexed else "新入库"
            print(f"    [Read] {label}: {paper_id}")

    if not ingested_ids:
        return {"errors": ["no papers could be ingested"], "paper_insights": []}

    # 2. 用 hybrid_search 搜一波大的，覆盖多篇论文
    chunks = await hybrid_search(query, n_results=50)

    if not chunks:
        return {"paper_insights": []}

    # 3. 按 paper_id 分组，每篇取前 3 个 chunk
    from collections import defaultdict
    paper_chunks = defaultdict(list)
    for c in chunks:
        pid = c["paper_id"]
        if pid in ingested_ids and len(paper_chunks[pid]) < 3:
            paper_chunks[pid].append(c)

    if not paper_chunks:
        return {"paper_insights": []}

    # 4. 拼接所有论文的 chunk，让 LLM 按论文分写总结
    context_parts = []
    paper_index = {}
    for idx, (pid, chs) in enumerate(paper_chunks.items(), 1):
        paper_index[str(idx)] = pid
        for ci, c in enumerate(chs, 1):
            context_parts.append(f"[Paper{idx} Chunk{ci}] {c['content'][:600]}")
    context = "\n\n".join(context_parts)

    client = AsyncOpenAI(
        api_key=settings.anthropic_api_key,
        base_url=settings.base_url,
        timeout=120.0,
        max_retries=2,
    )

    prompt = (
        f"Question: {query}\n\n"
        f"Below are excerpts from {len(paper_chunks)} papers. "
        f"For EACH paper, write a concise summary of its contribution to answering the question.\n\n"
        f"{context}\n\n"
        "Return ONLY valid JSON: {\"papers\": ["
        "{\"paper_num\": 1, \"summary\": \"This paper proposes...\"}, ...]}"
    )

    response = await client.chat.completions.create(
        model=settings.default_model,
        max_tokens=3000,
        messages=[
            {
                "role": "system",
                "content": (
                    "You read academic paper excerpts. "
                    "For each paper, summarize its key points concisely. "
                    "Cite specific methods, results, or claims. "
                    "Return ONLY valid JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )

    text = response.choices[0].message.content
    per_paper = _parse_paper_summaries(text, paper_index, query)

    return {
        "paper_insights": per_paper,
        "final_answer": "\n\n".join([
            f"**{ins['source']}**: {ins['answer']}"
            for ins in per_paper
        ]) if per_paper else "",
    }


def _parse_paper_summaries(text: str, paper_index: dict, query: str) -> list[dict]:
    """Parse LLM's JSON into per-paper insights."""
    text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
        else:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            data = json.loads(match.group(0)) if match else {}

    results = []
    for item in data.get("papers", []):
        num = str(item.get("paper_num", ""))
        source_id = paper_index.get(num, f"paper_{num}")
        results.append({
            "query": query,
            "answer": item.get("summary", ""),
            "source": source_id,
            "sources": [source_id],
        })
    return results
