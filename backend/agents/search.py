import logging
from backend.core.observability import logger, report_exception
import asyncio
import time
from backend.agents.state import ResearchState
from backend.sources.arxiv_client import search_arxiv
from backend.sources.semantic_scholar_client import search_semantic_scholar
from backend.sources.crossref_client import search_crossref
from backend.sources.pubmed_client import search_pubmed
from backend.config import settings
from backend.core.errors import AppError
from backend.services.paper_ranking import citation_count, rank_candidate_papers

SEARCH_TIMEOUT = settings.search_timeout_seconds  # 30s per-source timeout


async def search_papers(state: ResearchState) -> dict:
    plan = state.get("research_plan", [])
    results_per_source = settings.search_results_per_source
    if state.get("search_round", 0) >= settings.max_search_rounds:
        return {"raw_papers": state.get("raw_papers", []), "search_round": state["search_round"]}
    search_round = state.get("search_round", 0) + 1
    if not plan:
        return {
            "errors": ["no research plan to search"],
            "search_round": state.get("search_round", 0) + 1,
        }

    queries = [task["sub_query"][:200] for task in plan]
    t0 = time.time()
    logger.info(f"\n[Search] Starting {len(queries)} sub-queries across 4 sources (max {SEARCH_TIMEOUT}s per call)...")

    # Run ALL sub-queries × 4 sources fully concurrently
    async def search_one_query(q: str, idx: int):
        """Search all 4 sources for one sub-query in parallel, with logging."""
        q_t0 = time.time()
        logger.info("search.query.started", extra={"fields": {"query_index": idx + 1}})
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
                report_exception(r, "search.source.failed", level=logging.WARNING,
                                 source=src_name, query_index=idx + 1)
            elif isinstance(r, list):
                logger.info(f"    [Search] Q{idx+1} {src_name}: {len(r)} papers")
                for paper in r:
                    enriched = dict(paper)
                    enriched["search_round_found"] = search_round
                    matched_queries = list(enriched.get("matched_queries") or [])
                    if q not in matched_queries:
                        matched_queries.append(q)
                    enriched["matched_queries"] = matched_queries
                    papers.append(enriched)
            else:
                logger.info(f"    [Search] Q{idx+1} {src_name}: unexpected type {type(r)}")
        logger.info(f"  [Search] Q{idx+1} done in {time.time() - q_t0:.1f}s, total {len(papers)} papers")
        return papers

    # Fan out all sub-queries in parallel
    all_results = await asyncio.gather(
        *[search_one_query(q, i) for i, q in enumerate(queries)],
        return_exceptions=True,
    )

    all_papers = []
    for i, r in enumerate(all_results):
        if isinstance(r, Exception):
            report_exception(r, "search.query.failed", level=logging.WARNING, query_index=i + 1)
        elif isinstance(r, list):
            all_papers.extend(r)

    unique_papers = deduplicate_papers(
        state.get("raw_papers", []) + all_papers
    )
    unique_papers = cap_candidate_papers(unique_papers, settings.max_candidate_papers,
                                       state.get("user_query", ""))
    elapsed = time.time() - t0
    logger.info(f"[Search] All done in {elapsed:.1f}s → {len(unique_papers)} unique papers from {len(all_papers)} raw\n")

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
        doi = doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/").removeprefix("doi:").strip()
        title = " ".join(str(p.get("title") or "").lower().split())
        keys = []
        if doi:
            keys.append(("doi", doi))
        if title:
            keys.append(("title", title))
        existing_index = None
        for key in keys:
            if key not in seen:
                continue
            candidate_index = seen[key]
            existing_doi = str(unique[candidate_index].get("doi") or "").lower().strip()
            existing_doi = existing_doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/").removeprefix("doi:").strip()
            # Same title with distinct known DOIs can be different publications.
            if key[0] == "title" and doi and existing_doi and doi != existing_doi:
                continue
            existing_index = candidate_index
            break

        if existing_index is not None:
            existing = unique[existing_index]
            merged_queries = list(existing.get("matched_queries") or [])
            for query in p.get("matched_queries") or []:
                if query not in merged_queries:
                    merged_queries.append(query)
            existing["matched_queries"] = merged_queries
            incoming_count = citation_count(p)
            existing_count = citation_count(existing)
            if incoming_count is not None and (existing_count is None or incoming_count > existing_count):
                existing["citation_count"] = incoming_count
                existing["citation_count_known"] = True
                existing["citation_count_source"] = p.get("citation_count_source") or p.get("source", "")
            for field in ("abstract", "doi", "pdf_url", "published_date", "venue", "issns", "venue_quality"):
                if not existing.get(field) and p.get(field):
                    existing[field] = p[field]
            for key in keys:
                seen[key] = existing_index
            continue

        for key in keys:
            seen[key] = len(unique)
        unique.append(dict(p))
    return unique


def select_candidate_papers(state: ResearchState) -> dict:
    """在所有检索轮次结束后，按轮次和来源均衡选择候选论文。"""
    papers = state.get("raw_papers", [])
    limit = settings.max_candidate_papers
    if 0 < len(papers) < settings.min_candidate_papers:
        raise AppError(
            "SEARCH_TARGET_NOT_MET",
            f"检索到 {len(papers)} 篇去重论文，未达到 {settings.min_candidate_papers} 篇候选目标。请检查检索源可用性或调整查询范围。",
            422,
        )
    return {"raw_papers": cap_candidate_papers(papers, limit, state.get("user_query", ""))}


def cap_candidate_papers(papers: list[dict], limit: int, query: str = "") -> list[dict]:
    """Preserve source and retrieval-round coverage within the candidate cap."""
    papers = rank_candidate_papers(papers, query)
    if len(papers) <= limit:
        return papers

    buckets: dict[tuple[int, str], list[dict]] = {}
    for paper in papers:
        key = (
            int(paper.get("search_round_found") or 1),
            str(paper.get("source") or "unknown"),
        )
        buckets.setdefault(key, []).append(paper)

    # Global priority ordering already orders each source/round bucket.
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

    return sorted(selected, key=lambda paper: paper["candidate_priority_score"], reverse=True)
