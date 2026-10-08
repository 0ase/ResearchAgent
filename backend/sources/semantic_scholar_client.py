import logging
from backend.core.observability import logger, report_exception
import httpx
import asyncio

from backend.config import settings

BASE_URL = "https://api.semanticscholar.org/graph/v1"


async def search_semantic_scholar(query: str, max_results: int = 10, timeout: int = 30) -> list[dict]:
    """ use Semantic Scholar API to search paper"""
    url = f"{BASE_URL}/paper/search"
    params = {
        "query": query,
        "limit": min(max_results, 100),
        "fields": "title,authors,abstract,year,externalIds,citationCount,openAccessPdf,venue,publicationVenue,journal",
    }
    headers = {}
    if settings.semantic_scholar_api_key:
        headers["x-api-key"] = settings.semantic_scholar_api_key
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 429:
                    wait = 5 * (attempt + 1)
                    logger.warning("source.rate_limited", extra={"fields": {"source": "semantic_scholar", "attempt": attempt + 1, "retry_delay_seconds": wait}})
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                return _parse_response(data)
        except httpx.TimeoutException as exc:
            report_exception(exc, "source.timeout", level=logging.WARNING, source="semantic_scholar", attempt=attempt + 1)
            if attempt == 0:
                await asyncio.sleep(2)
                continue
        except Exception as e:
            report_exception(e, "source.failed", level=logging.WARNING, source="semantic_scholar", attempt=attempt + 1)
            if attempt == 0:
                await asyncio.sleep(2)
                continue
    return []


def _parse_response(data: dict) -> list[dict]:
    """Convert the S2 JSON response into a list of dictionaries in a unified format"""
    papers = []
    for item in data.get("data", []):
        publication_venue = item.get("publicationVenue") or {}
        journal = item.get("journal") or {}
        issn = publication_venue.get("issn")
        issns = ([issn] if isinstance(issn, str) else list(issn or []))
        issns.extend(publication_venue.get("alternate_issns") or [])
        papers.append({
            "title": item.get("title", "Untitled"),
            "authors": [a.get("name", "") for a in item.get("authors", [])],
            "abstract": item.get("abstract", ""),
            "source": "semantic_scholar",
            "source_id": f"semantic_scholar:{item.get('paperId', '')}",
            "published_date": str(item.get("year", "")),
            "doi": (item.get("externalIds") or {}).get("DOI", ""),
            "citation_count": item.get("citationCount", 0),
            "citation_count_known": item.get("citationCount") is not None,
            "citation_count_source": "semantic_scholar",
            "venue": publication_venue.get("name") or item.get("venue") or journal.get("name") or "",
            "issns": list(dict.fromkeys(issns)),
            "pdf_url": (item.get("openAccessPdf") or {}).get("url", ""),
        })
    return papers
