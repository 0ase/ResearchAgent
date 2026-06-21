import json
import re
import asyncio
from openai import AsyncOpenAI
from backend.agents.state import ResearchState
from backend.config import settings

BATCH_SIZE = 25
TOP_K = 20

async def filter_papers(state: ResearchState) -> dict:
    """Filter Agent: LLM scores all papers by abstract -> select top 20"""
    papers = state.get("raw_papers", [])
    query = state.get("user_query", "")

    if not query:
        return {"errors": ["no papers to filter"], "selected_papers": []}
    
    client = AsyncOpenAI(
        api_key=settings.anthropic_api_key,
        base_url=settings.base_url,
        timeout=120.0,
        max_retries=2,
    )

    sem = asyncio.Semaphore(3)

    async def score_batch(batch: list[dict], batch_idx: int) -> list[dict]:
        papers_text = "\n\n".join([
            f"[{batch_idx * BATCH_SIZE + i + 1}]"
            f"Title: {p.get('title', 'N/A')}\n"
            f"Abstract: {(p.get('abstract') or 'N/A')[:500]}"
            for i, p in enumerate(batch)
        ])

        prompt = (
            f"Research question: {query}\n\n"
            f"Below are {len(batch)} papers. For each, score relevance 1-5 "
            f"(5=highly relevant). Consider: topic match, methodology, recency.\n\n"
            f"{papers_text}\n\n"
            'Return ONLY valid JSON: '
            '{"scores": [{"paper_num": 1, "score": 4, "reason": "..."}]}'
        )

        async with sem:
            resp = await client.chat.completions.create(
                model=settings.light_model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You screen academic papers. "
                            "Score each paper's relevance to the research question (1-5). "
                            "Be strict. Return ONLY valid JSON."                        
                        ),
                    },
                    {"role": "user", "content": prompt}
                ],
            )

        text = resp.choices[0].message.content.strip()
        scores = _parse_scores(text)

        results = []
        for item in scores:
            idx = item.get("paper_num", 0) - batch_idx * BATCH_SIZE - 1
            if 0 <= idx < len(batch):
                p = dict(batch[idx])
                p["relevance_score"] = item.get("score", 0)
                p["relevance_reason"] = item.get("reason", "")
                results.append(p)
        return results

    batches = [papers[i:i + BATCH_SIZE] for i in range(0, len(papers), BATCH_SIZE)]
    tasks = [score_batch(b, i) for i, b in enumerate(batches)]

    all_results = await asyncio.gather(*tasks, return_exceptions=True)

    scored = []
    for r in all_results:
        if isinstance(r, list):
            scored.extend(r)
    
    scored.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)
    selected = scored[:TOP_K]

    print(f"\n[Filter] Scored {len(scored)} / {len(papers)} papers -> top {len(selected)}")
    for i, p in enumerate(selected[:5], 1):
        print(f"    {i}. [{p.get('relevance_score', '?')}/5] {p.get('title', '?')[:80]}")
    
    return {"selected_papers": selected}

def _parse_scores(text: str) -> list[dict]:
    text = text.strip()
    try:
        data = json.loads(text)
        return data.get("scores", [])
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            return data.get("scores", [])
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{.*\"scores\".*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return data.get("scores", [])
        except json.JSONDecodeError:
            pass
    return []