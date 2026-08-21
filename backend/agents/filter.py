import json
import re
import asyncio
from collections.abc import Iterable
from openai import AsyncOpenAI
from backend.agents.state import ResearchState
from backend.config import settings
from backend.repositories.paper_repository import PaperRepository
from backend.services.run_context import context_from_state

BATCH_SIZE = 25
RELEVANCE_THRESHOLD = 3

async def filter_papers(state: ResearchState) -> dict:
    """Filter Agent: score abstracts and select at most the task limit."""
    papers = state.get("raw_papers", [])
    query = state.get("user_query", "")
    max_papers = max(1, state.get("max_papers", 20))
    output_language = state.get("output_language", "en")
    context = context_from_state(state)

    if not query:
        return {"errors": ["no papers to filter"], "selected_papers": []}
    
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.base_url,
        timeout=120.0,
        max_retries=2,
    )

    sem = asyncio.Semaphore(3)

    async def score_batch(batch: list[dict], batch_idx: int) -> list[dict]:
        if context:
            context.raise_if_cancelled()
        papers_text = "\n\n".join([
            f"[{batch_idx * batch_size + i + 1}]"
            f"Title: {p.get('title', 'N/A')}\n"
            f"Abstract: {(p.get('abstract') or 'N/A')[:500]}"
            for i, p in enumerate(batch)
        ])

        prompt = (
            f"Research question: {query}\n\n"
            f"Below are {len(batch)} papers. For each, score relevance 1-5 "
            f"(5=highly relevant). Consider: topic match, methodology, recency.\n\n"
            f"{papers_text}\n\n"
            f"Return reasons in {output_language}. "
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
        if context:
            context.raise_if_cancelled()
        scores = _parse_scores(text)

        results = []
        for item in scores:
            idx = item.get("paper_num", 0) - batch_idx * batch_size - 1
            if 0 <= idx < len(batch):
                p = dict(batch[idx])
                p["relevance_score"] = item.get("score", 0)
                p["relevance_reason"] = item.get("reason", "")
                results.append(p)
        return results

    batch_size = max(1, min(BATCH_SIZE, max_papers))
    batches = [papers[i:i + batch_size] for i in range(0, len(papers), batch_size)]
    tasks = [score_batch(b, i) for i, b in enumerate(batches)]

    all_results = await asyncio.gather(*tasks, return_exceptions=True)

    scored = []
    warnings: list[str] = []
    for r in all_results:
        if isinstance(r, list):
            scored.extend(r)
        elif isinstance(r, Exception):
            warnings.append("FILTER_MODEL_FAILED")
    
    scored.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)
    selected = [
        paper
        for paper in scored
        if _as_float(paper.get("relevance_score")) is not None
        and float(paper.get("relevance_score")) >= RELEVANCE_THRESHOLD
    ][:max_papers]

    retrieval_queries = [
        str(item.get("retrieval_query") or "")
        for item in (state.get("research_plan") or [])
        if isinstance(item, dict)
    ]
    if not selected:
        warnings.append("FILTER_FALLBACK_USED")
        selected = _deterministic_rank(
            papers,
            query=query,
            retrieval_queries=retrieval_queries,
        )[:max_papers]
        scored = _merge_scored(scored, selected)
    selected = _ensure_source_diversity(
        selected,
        scored,
        max_papers=max_papers,
    )

    selected_ids = {
        paper.get("paper_id") or paper.get("id") or paper.get("source_id")
        for paper in selected
    }
    scored_by_id = {
        paper.get("paper_id") or paper.get("id") or paper.get("source_id"): paper
        for paper in scored
    }
    for paper in papers:
        paper_id = paper.get("paper_id") or paper.get("id") or paper.get("source_id")
        scored_paper = scored_by_id.get(paper_id)
        if scored_paper is not None:
            paper.update(
                {
                    "relevance_score": scored_paper.get("relevance_score"),
                    "relevance_reason": scored_paper.get("relevance_reason"),
                    "selected": paper_id in selected_ids,
                }
            )

    task_id = state.get("task_id")
    if task_id:
        repository = PaperRepository()
        for paper in scored:
            paper_id = paper.get("paper_id") or paper.get("id")
            if not paper_id:
                continue
            await repository.update_selection(
                task_id,
                paper_id,
                selected=paper_id in selected_ids,
                relevance_score=_as_float(paper.get("relevance_score")),
                relevance_reason=paper.get("relevance_reason"),
            )

    print(f"\n[Filter] Scored {len(scored)} / {len(papers)} papers -> top {len(selected)}")
    for i, p in enumerate(selected[:5], 1):
        print(f"    {i}. [{p.get('relevance_score', '?')}/5] {p.get('title', '?')[:80]}")
    
    return {"selected_papers": selected, "warnings": warnings}


def _as_float(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None

def _parse_scores(text: str) -> list[dict]:
    text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return _valid_scores(data)
        if isinstance(data, dict):
            return _valid_scores(data.get("scores", []))
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*([\[{].*?[\]}])\s*```", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            return _valid_scores(
                data if isinstance(data, list) else data.get("scores", [])
            )
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{.*\"scores\".*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return _valid_scores(data.get("scores", []))
        except json.JSONDecodeError:
            pass
    return []


def _valid_scores(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    valid = []
    for item in value:
        if not isinstance(item, dict):
            continue
        try:
            paper_num = int(item.get("paper_num"))
            score = max(1, min(5, int(float(item.get("score")))))
        except (TypeError, ValueError):
            continue
        valid.append(
            {
                "paper_num": paper_num,
                "score": score,
                "reason": str(item.get("reason") or ""),
            }
        )
    return valid


def _deterministic_score(
    paper: dict,
    *,
    query: str,
    retrieval_queries: Iterable[str],
) -> tuple[int, str]:
    search_text = " ".join(
        [query, *retrieval_queries]
    ).casefold()
    source_text = " ".join(
        [str(paper.get("title") or ""), str(paper.get("abstract") or "")]
    ).casefold()
    terms = {
        term
        for term in re.findall(r"[a-z][a-z0-9-]{2,}", search_text)
        if term
    }
    overlap = sorted(term for term in terms if term in source_text)
    score = min(5, 1 + len(overlap))
    if paper.get("abstract") or paper.get("pdf_url"):
        score = max(score, 2)
    return score, f"Matched terms: {', '.join(overlap[:6]) or 'no shared terms'}"


def _deterministic_rank(
    papers: list[dict],
    *,
    query: str,
    retrieval_queries: Iterable[str],
) -> list[dict]:
    ranked = []
    for paper in papers:
        if not paper.get("abstract") and not paper.get("pdf_url"):
            continue
        score, reason = _deterministic_score(
            paper,
            query=query,
            retrieval_queries=retrieval_queries,
        )
        item = dict(paper)
        item["relevance_score"] = score
        item["relevance_reason"] = reason
        ranked.append(item)
    return sorted(
        ranked,
        key=lambda item: (
            item.get("relevance_score", 0),
            bool(item.get("abstract")),
            bool(item.get("pdf_url")),
        ),
        reverse=True,
    )


def _ensure_source_diversity(
    selected: list[dict],
    scored: list[dict],
    *,
    max_papers: int,
) -> list[dict]:
    if max_papers < 2 or len({paper.get("source") for paper in selected}) >= 2:
        return selected
    selected_ids = {
        paper.get("paper_id") or paper.get("source_id") for paper in selected
    }
    selected_sources = {paper.get("source") for paper in selected}
    replacement = next(
        (
            paper
            for paper in scored
            if (paper.get("source") not in selected_sources)
            and (paper.get("paper_id") or paper.get("source_id")) not in selected_ids
            and float(paper.get("relevance_score") or 0) >= RELEVANCE_THRESHOLD
        ),
        None,
    )
    if replacement is None:
        return selected
    return [*selected[: max_papers - 1], replacement]


def _merge_scored(existing: list[dict], additions: list[dict]) -> list[dict]:
    by_id = {
        paper.get("paper_id") or paper.get("id") or paper.get("source_id"): paper
        for paper in existing
    }
    for paper in additions:
        key = paper.get("paper_id") or paper.get("id") or paper.get("source_id")
        if key:
            by_id[key] = paper
    return list(by_id.values())
