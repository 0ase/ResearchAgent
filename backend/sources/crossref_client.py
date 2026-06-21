import asyncio
import httpx

BASE_URL = "https://api.crossref.org/works"


async def search_crossref(query: str, max_results: int = 10, timeout: int = 30) -> list[dict]:
    """use crossref api to search papers"""
    url = BASE_URL
    params = {
        "query": query,
        "rows": min(max_results, 100),
        "sort": "relevance",
    }

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 429:
                    wait = 5 * (attempt + 1)
                    print(f"    [crossref] 429 rate limited, waiting {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return _parse_response(resp.json())
        except httpx.TimeoutException:
            if attempt == 0:
                print(f"    [crossref] timeout ({timeout}s), retrying...")
                await asyncio.sleep(2)
                continue
            print(f"    [crossref] timeout after retry, giving up")
        except Exception as e:
            if attempt == 0:
                await asyncio.sleep(2)
                continue
            print(f"    [crossref] error: {type(e).__name__}: {e}")
    return []


def _parse_response(data: dict) -> list[dict]:
    """parse Crossref JSON to Unified format"""
    papers = []
    for item in data.get("message", {}).get("items", []):
        # author
        authors = []
        for a in item.get("author", []):
            given = a.get("given", "")
            family = a.get("family", "")
            name = f"{given} {family}".strip()
            if name:
                authors.append(name)

        # Title
        title_list = item.get("title", ["Untitled"])
        title = title_list[0] if title_list else "Untitled"

        # DOI
        doi = item.get("DOI", "")

        # Date
        date_parts = item.get("published", {}).get("date-parts", [[None]])[0]
        year = str(date_parts[0]) if date_parts and date_parts[0] else ""

        papers.append({
            "title": title,
            "authors": authors,
            "abstract": item.get("abstract", ""),
            "source": "crossref",
            "source_id": f"crossref:{doi}",
            "published_date": year,
            "doi": doi,
            "citation_count": item.get("is-referenced-by-count", 0),
            "pdf_url": ""
        })

    return papers
