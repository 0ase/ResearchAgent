import asyncio
from backend.agents.state import ResearchState
from backend.sources.arxiv_client import search_arxiv
from backend.sources.semantic_scholar_client import search_semantic_scholar
from backend.sources.crossref_client import search_crossref
from backend.sources.pubmed_client import search_pubmed

async def search_papers(state: ResearchState) -> dict:
    plan = state.get("research_plan", [])
    if not plan:
        return {"errors": ["no research plan to return"], "search_round": state["search_round"] + 1}

    queries = [task["sub_query"][:200] for task in plan]

    all_papers = []
    for q in queries:
        arxiv_papers, s2_papers, pubmed_papers, crossref_papers = await asyncio.gather(
            search_arxiv(q),
            search_semantic_scholar(q),
            search_pubmed(q),
            search_crossref(q),
        )
        all_papers.extend(arxiv_papers)
        all_papers.extend(s2_papers)
        all_papers.extend(pubmed_papers)
        all_papers.extend(crossref_papers)
        await asyncio.sleep(3)
    unique_papers = deduplicate_papers(all_papers)

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
