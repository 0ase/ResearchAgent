import asyncio
import time
from backend.agents.state import ResearchState
from backend.sources.arxiv_client import search_arxiv
from backend.sources.semantic_scholar_client import search_semantic_scholar
from backend.sources.crossref_client import search_crossref
from backend.sources.pubmed_client import search_pubmed
from backend.config import settings

SEARCH_TIMEOUT = settings.search_timeout_seconds  # 30s per-source timeout


async def search_papers(state: ResearchState) -> dict:
    plan = state.get("research_plan", [])
    results_per_source = settings.search_results_per_source
    search_round = state.get("search_round", 0) + 1
    if not plan:
        return {
            "errors": ["no research plan to search"],
            "search_round": state.get("search_round", 0) + 1,
        }

    queries = [task["sub_query"][:200] for task in plan]
    t0 = time.time()
    print(f"\n[Search] Starting {len(queries)} sub-queries across 4 sources (max {SEARCH_TIMEOUT}s per call)...")

    # Run ALL sub-queries × 4 sources fully concurrently
    async def search_one_query(q: str, idx: int):
        """Search all 4 sources for one sub-query in parallel, with logging."""
        q_t0 = time.time()
        print(f"  [Search] Q{idx+1}: \"{q[:80]}...\" → searching 4 sources...")
        results = await asyncio.gather(
            search_arxiv(q, max_results=results_per_source, timeout=SEARCH_TIMEOUT),
            search_semantic_scholar(q, max_results=results_per_source, timeout=SEARCH_TIMEOUT),
            search_pubmed(q, max_results=results_per_source, timeout=SEARCH_TIMEOUT),
            search_crossref(q, max_results=results_per_source, timeout=SEARCH_TIMEOUT),
            return_exceptions=True,
        )
        papers = []
        source_names = ["arxiv", "semantic_scholar", "pubmed", "crossref"]
        for src_name, r in zip(source_names, results):
            if isinstance(r, Exception):
                print(f"    [Search] Q{idx+1} {src_name}: ERROR - {r}")
            elif isinstance(r, list):
                print(f"    [Search] Q{idx+1} {src_name}: {len(r)} papers")
                for paper in r:
                    enriched = dict(paper)
                    enriched["search_round_found"] = search_round
                    matched_queries = list(enriched.get("matched_queries") or [])
                    if q not in matched_queries:
                        matched_queries.append(q)
                    enriched["matched_queries"] = matched_queries
                    papers.append(enriched)
            else:
                print(f"    [Search] Q{idx+1} {src_name}: unexpected type {type(r)}")
        print(f"  [Search] Q{idx+1} done in {time.time() - q_t0:.1f}s, total {len(papers)} papers")
        return papers

    # Fan out all sub-queries in parallel
    all_results = await asyncio.gather(
        *[search_one_query(q, i) for i, q in enumerate(queries)],
        return_exceptions=True,
    )

    all_papers = []
    for i, r in enumerate(all_results):
        if isinstance(r, Exception):
            print(f"  [Search] Q{i+1} failed entirely: {r}")
        elif isinstance(r, list):
            all_papers.extend(r)

    unique_papers = deduplicate_papers(
        state.get("raw_papers", []) + all_papers
    )
    elapsed = time.time() - t0
    print(f"[Search] All done in {elapsed:.1f}s → {len(unique_papers)} unique papers from {len(all_papers)} raw\n")

    return {
        "raw_papers": unique_papers,
        "search_round": search_round,
    }


def deduplicate_papers(papers: list[dict]) -> list[dict]:
    """按 DOI/标题去重，并合并论文命中的查询。"""
    seen: dict[tuple[str, str], int] = {}
    unique: list[dict] = []

    for p in papers:
        doi = str(p.get("doi") or "").lower().strip()
        title = str(p.get("title") or "").lower().strip()
        key = ("doi", doi) if doi else (("title", title) if title else None)

        if key is not None and key in seen:
            existing = unique[seen[key]]
            merged_queries = list(existing.get("matched_queries") or [])
            for query in p.get("matched_queries") or []:
                if query not in merged_queries:
                    merged_queries.append(query)
            existing["matched_queries"] = merged_queries
            continue

        if key is not None:
            seen[key] = len(unique)
        unique.append(dict(p))
    return unique


def select_candidate_papers(state: ResearchState) -> dict:
    """在所有检索轮次结束后，按轮次和来源均衡选择候选论文。"""
    papers = state.get("raw_papers", [])
    limit = settings.max_candidate_papers
    if len(papers) <= limit:
        return {}

    buckets: dict[tuple[int, str], list[dict]] = {}
    for paper in papers:
        key = (
            int(paper.get("search_round_found") or 1),
            str(paper.get("source") or "unknown"),
        )
        buckets.setdefault(key, []).append(paper)

    # 每个桶内优先保留有摘要、引用量较高的论文。
    for bucket in buckets.values():
        bucket.sort(
            key=lambda paper: (
                bool((paper.get("abstract") or "").strip()),
                int(paper.get("citation_count") or 0),
            ),
            reverse=True,
        )

    selected: list[dict] = []
    active_keys = list(buckets)
    while active_keys and len(selected) < limit:
        next_keys = []
        for key in active_keys:
            bucket = buckets[key]
            if bucket and len(selected) < limit:
                selected.append(bucket.pop(0))
            if bucket:
                next_keys.append(key)
        active_keys = next_keys

    return {"raw_papers": selected}
