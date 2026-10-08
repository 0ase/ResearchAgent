import logging
from backend.core.observability import logger, report_exception
import xml.etree.ElementTree as ET
import httpx
import asyncio


async def search_arxiv(query: str, max_results: int = 10, timeout: int = 30) -> list[dict]:
    """use arxiv API to get the raw papers"""
    url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": f"all: {query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    for attempt in range(2):  # reduced from 3 to 2 attempts
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 429:
                    wait = 5 * (attempt + 1)
                    logger.warning("source.rate_limited", extra={"fields": {"source": "arxiv", "attempt": attempt + 1, "retry_delay_seconds": wait}})
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return parse_arxiv_response(resp.text)
        except httpx.TimeoutException as exc:
            report_exception(exc, "source.timeout", level=logging.WARNING, source="arxiv", attempt=attempt + 1)
            if attempt == 0:
                await asyncio.sleep(2)
                continue
        except Exception as e:
            report_exception(e, "source.failed", level=logging.WARNING, source="arxiv", attempt=attempt + 1)
            if attempt == 0:
                await asyncio.sleep(2)
                continue

    return []


def parse_arxiv_response(xml_text: str) -> list[dict]:
    """Parse the XML text returned by arXiv into a list of paper dictionaries"""
    root = ET.fromstring(xml_text)
    papers = []

    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

    for entry in root.findall("atom:entry", ns):
        title = entry.find("atom:title", ns)
        summary = entry.find("atom:summary", ns)

        authors = []
        for author in entry.findall("atom:author", ns):
            name = author.find("atom:name", ns)
            if name is not None and name.text:
                authors.append(name.text)

        # Extract the arXiv ID (obtained by extracting from the URL)
        id_url = entry.find("atom:id", ns)
        arxiv_id = ""
        if id_url is not None and id_url.text:
            # "http://arxiv.org/abs/2301.12345v1" → "2301.12345"
            arxiv_id = id_url.text.split("/abs/")[-1].split("v")[0]

        papers.append({
            "title": title.text.strip() if title is not None and title.text else "Untitled",
            "authors": authors,
            "abstract": summary.text.strip() if summary is not None and summary.text else "",
            "source": "arxiv",
            "source_id": f"arxiv:{arxiv_id}",
            "published_date": entry.findtext("atom:published", default="", namespaces=ns),
            "venue": entry.findtext("arxiv:journal_ref", default="", namespaces=ns),
            "citation_count_known": False,
            "arxiv_id": arxiv_id,
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else "",
        })
    return papers
