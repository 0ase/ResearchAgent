import asyncio
import httpx
from backend.agents.state import ResearchState
from backend.config import settings
from backend.sources.arxiv_client import parse_arxiv_response


async def search_arxiv(query: str, max_results: int = 10) -> list[dict]:
    """use arxiv API to get the raw papers"""
    url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": f"all: {query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 429:
                    wait = 10 * (attempt + 1)
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return parse_arxiv_response(resp.text)
        except httpx.ReadTimeout:
            wait = 5 * (attempt + 1)
            await asyncio.sleep(wait)
            continue
        except Exception:
            await asyncio.sleep(5)
            continue

    return []


async def search_papers(state: ResearchState) -> dict:
    plan = state.get("research_plan", [])
    if not plan:
        return {"errors": ["no research plan to return"], "search_round": state["search_round"] + 1}

    queries = [task["sub_query"][:200] for task in plan]

    all_papers = []
    for q in queries:
        papers = await search_arxiv(q)
        all_papers.extend(papers)
        await asyncio.sleep(4)

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
