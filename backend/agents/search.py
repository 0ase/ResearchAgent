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
    max_papers = state.get("max_papers", 10)
    if not plan:
        return {"errors": ["no research plan to return"], "search_round": state["search_round"] + 1}

    queries = [task["sub_query"][:200] for task in plan]
    t0 = time.time()
    print(f"\n[Search] Starting {len(queries)} sub-queries across 4 sources (max {SEARCH_TIMEOUT}s per call)...")

    # Run ALL sub-queries × 4 sources fully concurrently
    async def search_one_query(q: str, idx: int):
        """Search all 4 sources for one sub-query in parallel, with logging."""
        q_t0 = time.time()
        print(f"  [Search] Q{idx+1}: \"{q[:80]}...\" → searching 4 sources...")
        results = await asyncio.gather(
            search_arxiv(q, max_results=max_papers, timeout=SEARCH_TIMEOUT),
            search_semantic_scholar(q, max_results=max_papers, timeout=SEARCH_TIMEOUT),
            search_pubmed(q, max_results=max_papers, timeout=SEARCH_TIMEOUT),
            search_crossref(q, max_results=max_papers, timeout=SEARCH_TIMEOUT),
            return_exceptions=True,
        )
        papers = []
        source_names = ["arxiv", "semantic_scholar", "pubmed", "crossref"]
        for src_name, r in zip(source_names, results):
            if isinstance(r, Exception):
                print(f"    [Search] Q{idx+1} {src_name}: ERROR - {r}")
            elif isinstance(r, list):
                print(f"    [Search] Q{idx+1} {src_name}: {len(r)} papers")
                papers.extend(r)
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

    unique_papers = deduplicate_papers(all_papers)
    elapsed = time.time() - t0
    print(f"[Search] All done in {elapsed:.1f}s → {len(unique_papers)} unique papers from {len(all_papers)} raw\n")

    return {
        "raw_papers": unique_papers,
        "search_round": state["search_round"] + 1,
    }


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
