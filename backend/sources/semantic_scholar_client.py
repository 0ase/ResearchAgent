import httpx
import asyncio

BASE_URL = "https://api.semanticscholar.org/graph/v1"

async def search_semantic_scholar(query: str, max_results: int = 10) -> list[dict]:
    """ use Semantic Scholar API to search paper"""
    url = f"{BASE_URL}/paper/search"
    params = {
        "query": query,
        "limit": min(max_results, 100),
        "fields": "title,authors,abstract,year,externalIds,citationCount,openAccessPdf",
    }
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 429:
                    wait = 10 * (attempt + 1)
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                return _parse_response(data)
        except Exception:
            await asyncio.sleep(5)
            continue
    return []

def _parse_response(data: dict) -> list[dict]:
    """Convert the S2 JSON response into a list of dictionaries in a unified format"""
    papers = []
    for item in data.get("data", []):
        papers.append({
            "title": item.get("title", "Untitled"),
            "authors": [a.get("name", "") for a in item.get("authors", [])],
            "abstract": item.get("abstract", ""),
            "source": "semantic_scholar",
            "source_id": f"semantic_scholar:{item.get('paperId', '')}",
            "published_date": str(item.get("year", "")),
            "doi": (item.get("externalIds") or {}).get("DOI", ""),
            "citation_count": item.get("citationCount", 0),
            "pdf_url": (item.get("openAccessPdf") or {}).get("url", ""),
        })
    return papers