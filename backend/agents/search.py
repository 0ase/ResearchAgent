import asyncio
import time
from backend.agents.state import ResearchState
from backend.sources.arxiv_client import search_arxiv
from backend.sources.semantic_scholar_client import search_semantic_scholar
from backend.sources.crossref_client import search_crossref
from backend.sources.pubmed_client import search_pubmed
from backend.config import settings
from backend.services.run_context import context_from_state
from backend.services.paper_normalizer import normalize_paper
from backend.repositories.paper_repository import PaperRepository

SEARCH_TIMEOUT = settings.search_timeout_seconds  # 30s per-source timeout
SOURCE_CLIENTS = None


async def search_papers(state: ResearchState) -> dict:
    context = context_from_state(state)
    if context:
        context.raise_if_cancelled()
    diagnostics = []
    providers = {"arxiv": search_arxiv, "semantic_scholar": search_semantic_scholar, "pubmed": search_pubmed, "crossref": search_crossref}
    providers = SOURCE_CLIENTS or providers
    source_names = [s for s in (state.get("sources") or list(providers)) if s in providers]
    plan = state.get("research_plan", [])
    results_per_source = settings.search_results_per_source
    search_round = state.get("search_round", 0) + 1
    if not plan:
        return {
            "errors": ["no research plan to search"],
            "search_round": state.get("search_round", 0) + 1,
        }

    queries = [str(task.get("retrieval_query") or task.get("sub_query") or "")[:200] for task in plan]
    t0 = time.time()
    print(f"\n[Search] Starting {len(queries)} sub-queries across 4 sources (max {SEARCH_TIMEOUT}s per call)...")

    # Run ALL sub-queries × 4 sources fully concurrently
    async def search_one_query(q: str, idx: int):
        """Search all 4 sources for one sub-query in parallel, with logging."""
        q_t0 = time.time()
        print(f"  [Search] Q{idx+1}: \"{q[:80]}...\" → searching 4 sources...")
        results = await asyncio.gather(
            *(providers[name](q, max_results=results_per_source, timeout=SEARCH_TIMEOUT) for name in source_names),
            return_exceptions=True,
        )
        papers = []
        for src_name, r in zip(source_names, results):
            if isinstance(r, asyncio.CancelledError):
                raise r
            diagnostics.append({"source": src_name, "query": q, "status": "error" if isinstance(r, Exception) else "ok", "papers": len(r) if isinstance(r, list) else 0, "error_code": getattr(r, "code", "SOURCE_REQUEST_FAILED") if isinstance(r, Exception) else None})
            if isinstance(r, Exception):
                print(f"    [Search] Q{idx+1} {src_name}: ERROR - {type(r).__name__}")
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
            print(f"  [Search] Q{i+1} failed entirely: {type(r).__name__}")
        elif isinstance(r, list):
            all_papers.extend(r)

    unique_papers = deduplicate_papers(
        state.get("raw_papers", []) + all_papers
    )
    if context:
        context.raise_if_cancelled()
    if state.get("task_id"):
        normalized = [normalize_paper(p, task_id=state["task_id"]) for p in unique_papers]
        stored = await PaperRepository().upsert_task_papers(state["task_id"], normalized)
        by_key = {p.canonical_id: p for p in stored}
        unique_papers = [{**raw, **by_key.get(p.canonical_id, p).model_dump(mode="json")} for raw, p in zip(unique_papers, normalized)]
    elapsed = time.time() - t0
    print(f"[Search] All done in {elapsed:.1f}s → {len(unique_papers)} unique papers from {len(all_papers)} raw\n")

    return {
        "raw_papers": unique_papers,
        "search_diagnostics": [*state.get("search_diagnostics", []), *diagnostics],
        "warnings": [d["error_code"] for d in diagnostics if d["error_code"]],
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

    # Read evidence remains authoritative across retrieval rounds. Reserve its
    # metadata before capping candidates, or result validation loses the paper.
    retained_ids = {i.get("paper_id") or i.get("source") for i in state.get("paper_insights", [])
                    if i.get("paper_id") or i.get("source")}
    selected = [p for p in papers if (p.get("paper_id") or p.get("source_id")) in retained_ids]
    buckets: dict[tuple[int, str], list[dict]] = {}
    for paper in papers:
        if (paper.get("paper_id") or paper.get("source_id")) in retained_ids:
            continue
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
