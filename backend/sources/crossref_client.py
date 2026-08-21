import asyncio
import httpx

from backend.sources.errors import SourceSearchError

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
                    if attempt == 0:
                        wait = 5 * (attempt + 1)
                        print(f"    [crossref] 429 rate limited, waiting {wait}s...")
                        await asyncio.sleep(wait)
                        continue
                    raise SourceSearchError(
                        "crossref",
                        "SOURCE_RATE_LIMITED",
                        "crossref rate limit reached",
                    )
                resp.raise_for_status()
                return _parse_response(resp.json())
        except httpx.TimeoutException as exc:
            if attempt == 0:
                print(f"    [crossref] timeout ({timeout}s), retrying...")
                await asyncio.sleep(2)
                continue
            print(f"    [crossref] timeout after retry, giving up")
            raise SourceSearchError(
                "crossref",
                "SOURCE_TIMEOUT",
                "crossref request timed out",
            ) from exc
        except httpx.HTTPStatusError as exc:
            if attempt == 0:
                await asyncio.sleep(2)
                continue
            raise SourceSearchError(
                "crossref",
                "SOURCE_HTTP_ERROR",
                "crossref returned an HTTP error",
            ) from exc
        except (TypeError, ValueError) as exc:
            raise SourceSearchError(
                "crossref",
                "SOURCE_RESPONSE_INVALID",
                "crossref returned an invalid response",
            ) from exc
        except Exception as exc:
            if attempt == 0:
                await asyncio.sleep(2)
                continue
            print(f"    [crossref] error: {type(exc).__name__}: {exc}")
            raise SourceSearchError(
                "crossref",
                "SOURCE_HTTP_ERROR",
                "crossref request failed",
            ) from exc
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
