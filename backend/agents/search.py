import asyncio
import time
from collections import defaultdict

from backend.agents.state import ResearchState
from backend.sources.arxiv_client import search_arxiv
from backend.sources.semantic_scholar_client import search_semantic_scholar
from backend.sources.crossref_client import search_crossref
from backend.sources.pubmed_client import search_pubmed
from backend.config import settings
from backend.repositories.paper_repository import PaperRepository
from backend.services.paper_normalizer import normalize_papers
from backend.services.run_context import context_from_state
from backend.sources.errors import SourceSearchError

SEARCH_TIMEOUT = settings.search_timeout_seconds  # 30s per-source timeout

SOURCE_CLIENTS = {
    "arxiv": search_arxiv,
    "semantic_scholar": search_semantic_scholar,
    "pubmed": search_pubmed,
    "crossref": search_crossref,
}


async def search_papers(state: ResearchState) -> dict:
    plan = state.get("research_plan", [])
    max_papers = state.get("max_papers", 10)
    selected_sources = [
        source for source in (state.get("sources") or SOURCE_CLIENTS)
        if source in SOURCE_CLIENTS
    ]
    context = context_from_state(state)
    if not plan:
        return {"errors": ["no research plan to return"], "search_round": state["search_round"] + 1}
    if not selected_sources:
        return {"errors": ["no research sources selected"], "search_round": state["search_round"] + 1}

    queries = [_query_spec(task) for task in plan]
    t0 = time.time()
    print(f"\n[Search] Starting {len(queries)} sub-queries across {len(selected_sources)} sources (max {SEARCH_TIMEOUT}s per call)...")

    # Run ALL sub-queries × 4 sources fully concurrently
    async def search_one_query(query_spec: dict[str, str], idx: int):
        """Search all selected sources and retain source-level diagnostics."""
        q_t0 = time.time()
        retrieval_query = query_spec["retrieval_query"] or query_spec["display_query"]
        display_query = query_spec["display_query"]
        print(
            f"  [Search] Q{idx+1}: \"{retrieval_query[:80]}...\" "
            f"→ searching {len(selected_sources)} sources..."
        )
        if context:
            context.raise_if_cancelled()
        results = await asyncio.gather(
            *[
                _search_source(
                    source,
                    retrieval_query=retrieval_query,
                    display_query=display_query,
                    max_results=max_papers,
                )
                for source in selected_sources
            ],
            return_exceptions=True,
        )
        papers = []
        diagnostics = []
        for src_name, r in zip(selected_sources, results):
            if isinstance(r, SourceSearchError):
                print(f"    [Search] Q{idx+1} {src_name}: ERROR - {r.code}")
                diagnostics.append(
                    {
                        "source": src_name,
                        "query_index": idx + 1,
                        "status": "error",
                        "papers": 0,
                        "error_code": r.code,
                    }
                )
            elif isinstance(r, Exception):
                print(f"    [Search] Q{idx+1} {src_name}: ERROR - {type(r).__name__}")
                diagnostics.append(
                    {
                        "source": src_name,
                        "query_index": idx + 1,
                        "status": "error",
                        "papers": 0,
                        "error_code": "SOURCE_HTTP_ERROR",
                    }
                )
            elif isinstance(r, tuple):
                source_papers, source_query = r
                print(f"    [Search] Q{idx+1} {src_name}: {len(source_papers)} papers")
                papers.extend(source_papers)
                diagnostics.append(
                    {
                        "source": src_name,
                        "query_index": idx + 1,
                        "status": "ok" if source_papers else "no_results",
                        "papers": len(source_papers),
                        "query_language": "zh-CN" if source_query == display_query and source_query != retrieval_query else "en",
                    }
                )
            else:
                print(f"    [Search] Q{idx+1} {src_name}: unexpected result")
                diagnostics.append(
                    {
                        "source": src_name,
                        "query_index": idx + 1,
                        "status": "error",
                        "papers": 0,
                        "error_code": "SOURCE_RESPONSE_INVALID",
                    }
                )
        print(f"  [Search] Q{idx+1} done in {time.time() - q_t0:.1f}s, total {len(papers)} papers")
        if context:
            context.raise_if_cancelled()
        return papers, diagnostics

    # Fan out all sub-queries in parallel
    all_results = await asyncio.gather(
        *[search_one_query(query, i) for i, query in enumerate(queries)],
        return_exceptions=True,
    )

    all_papers = []
    search_diagnostics: list[dict] = []
    for i, r in enumerate(all_results):
        if isinstance(r, Exception):
            print(f"  [Search] Q{i+1} failed entirely: {r}")
            search_diagnostics.append(
                {
                    "source": "query",
                    "query_index": i + 1,
                    "status": "error",
                    "papers": 0,
                    "error_code": "SEARCH_QUERY_FAILED",
                }
            )
        elif isinstance(r, tuple):
            papers, diagnostics = r
            all_papers.extend(papers)
            search_diagnostics.extend(diagnostics)

    existing_papers = state.get("raw_papers", []) or []
    task_id = state.get("task_id")
    normalized = normalize_papers(
        all_papers,
        task_id=task_id or "unassigned",
    )
    normalized = [
        paper
        for paper in normalized
        if not _paper_matches_existing(paper, existing_papers)
        and paper.full_text_status != "unavailable"
    ]
    normalized = _select_balanced_papers(
        normalized,
        max(0, max_papers - len(existing_papers)),
    )
    elapsed = time.time() - t0
    print(f"[Search] All done in {elapsed:.1f}s → {len(normalized)} unique papers from {len(all_papers)} raw\n")

    persistence_errors: list[str] = []
    if task_id:
        try:
            normalized = await PaperRepository().upsert_task_papers(task_id, normalized)
        except Exception as exc:
            print(f"[Search] paper snapshot persistence failed: {type(exc).__name__}: {exc}")
            persistence_errors.append("paper snapshot persistence failed")

    return {
        "raw_papers": [paper.to_result_dict() for paper in normalized],
        "search_round": state["search_round"] + 1,
        "errors": persistence_errors,
        "warnings": _diagnostic_warnings(search_diagnostics, normalized),
        "search_diagnostics": search_diagnostics,
    }


async def _search_source(
    source: str,
    *,
    retrieval_query: str,
    display_query: str,
    max_results: int,
) -> tuple[list[dict], str]:
    query = retrieval_query or display_query
    try:
        papers = await SOURCE_CLIENTS[source](
            query,
            max_results=max_results,
            timeout=SEARCH_TIMEOUT,
        )
    except SourceSearchError:
        raise

    if papers or source != "crossref" or display_query == retrieval_query:
        return papers, query

    # Crossref is the only selected provider for which a Chinese fallback query
    # is useful when the English query has no result.
    fallback_papers = await SOURCE_CLIENTS[source](
        display_query,
        max_results=max_results,
        timeout=SEARCH_TIMEOUT,
    )
    return fallback_papers, display_query


def _paper_matches_existing(paper, existing_papers: list[dict]) -> bool:
    keys = {
        paper.paper_id,
        paper.canonical_id,
        paper.source_id,
        paper.title.casefold().strip(),
    }
    for existing in existing_papers:
        existing_keys = {
            existing.get("paper_id"),
            existing.get("canonical_id"),
            existing.get("source_id"),
            str(existing.get("title") or "").casefold().strip(),
        }
        if keys & existing_keys:
            return True
    return False


def _query_spec(task: dict | str) -> dict[str, str]:
    """Normalize current and legacy research-plan entries."""
    if isinstance(task, dict):
        display_query = task.get("display_query") or task.get("sub_query") or ""
        retrieval_query = task.get("retrieval_query") or display_query
    else:
        display_query = str(task or "")
        retrieval_query = display_query
    return {
        "display_query": str(display_query).strip()[:200],
        "retrieval_query": str(retrieval_query).strip()[:200],
    }


def _select_balanced_papers(papers: list, limit: int) -> list:
    if limit <= 0:
        return []
    pools: dict[str, list] = defaultdict(list)
    for paper in sorted(papers, key=_paper_sort_key, reverse=True):
        pools[paper.source].append(paper)

    selected = []
    while pools and len(selected) < limit:
        for source in list(pools):
            if not pools[source]:
                del pools[source]
                continue
            selected.append(pools[source].pop(0))
            if len(selected) >= limit:
                break
            if not pools[source]:
                del pools[source]
    return selected


def _paper_sort_key(paper) -> tuple[int, int, int]:
    status_rank = {
        "full": 4,
        "abstract_only": 3,
        "full_no_abstract": 2,
        "pdf_failed": 1,
        "unavailable": 0,
    }
    return (
        status_rank.get(paper.full_text_status, 0),
        int(paper.citation_count or 0),
        int(paper.year or 0),
    )


def _diagnostic_warnings(diagnostics: list[dict], papers: list) -> list[str]:
    warnings = []
    for item in diagnostics:
        if item.get("status") == "error":
            warnings.append(
                f"{item.get('source', 'source')}:{item.get('error_code', 'SOURCE_ERROR')}"
            )
    sources = {paper.source for paper in papers}
    if len(sources) < 2:
        warnings.append("SOURCE_DIVERSITY_INSUFFICIENT")
    return warnings


def deduplicate_papers(papers: list[dict]) -> list[dict]:
    """use DOI and title to deduplicate"""
    seen_dois = set()
    seen_titles = set()
    unique = []

    for p in papers:
        doi = p.get("doi", "").lower()
        title = p.get("title", "").lower().strip()

        if doi and doi in seen_dois:
            continue

        if title in seen_titles:
            continue

        if doi:
            seen_dois.add(doi)
        seen_titles.add(title)
        unique.append(p)
    return unique
