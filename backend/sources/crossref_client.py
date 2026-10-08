import logging
from backend.core.observability import logger, report_exception
import asyncio
import httpx

from backend.config import settings

BASE_URL = "https://api.crossref.org/works"


async def search_crossref(query: str, max_results: int = 10, timeout: int = 30) -> list[dict]:
    """use crossref api to search papers"""
    url = BASE_URL
    params = {
        "query": query,
        "rows": min(max_results, 100),
        "sort": "relevance",
    }
    if settings.crossref_email:
        params["mailto"] = settings.crossref_email
    headers = {
        "User-Agent": (
            f"BIGONE/1.0 (mailto:{settings.crossref_email})"
            if settings.crossref_email
            else "BIGONE/1.0"
        )
    }

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 429:
                    wait = 5 * (attempt + 1)
                    logger.warning("source.rate_limited", extra={"fields": {"source": "crossref", "attempt": attempt + 1, "retry_delay_seconds": wait}})
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return _parse_response(resp.json())
        except httpx.TimeoutException as exc:
            report_exception(exc, "source.timeout", level=logging.WARNING, source="crossref", attempt=attempt + 1)
            if attempt == 0:
                await asyncio.sleep(2)
                continue
        except Exception as e:
            report_exception(e, "source.failed", level=logging.WARNING, source="crossref", attempt=attempt + 1)
            if attempt == 0:
                await asyncio.sleep(2)
                continue
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
        venues = item.get("container-title") or []
        pdf_url = next((link.get("URL", "") for link in (item.get("link") or [])
                        if isinstance(link, dict) and link.get("content-type") == "application/pdf"), "")

        papers.append({
            "title": title,
            "authors": authors,
            "abstract": item.get("abstract", ""),
            "source": "crossref",
            "source_id": f"crossref:{doi}",
            "published_date": year,
            "doi": doi,
            "citation_count": item.get("is-referenced-by-count", 0),
            "citation_count_known": item.get("is-referenced-by-count") is not None,
            "citation_count_source": "crossref",
            "venue": venues[0] if venues else "",
            "issns": item.get("ISSN") or [],
            "pdf_url": pdf_url,
        })

    return papers
