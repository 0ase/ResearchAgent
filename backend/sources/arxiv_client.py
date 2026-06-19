import xml.etree.ElementTree as ET
import httpx
import asyncio

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

def parse_arxiv_response(xml_text: str) -> list[dict]:
    """Parse the XML text returned by arXiv into a list of paper dictionaries"""
    root = ET.fromstring(xml_text)
    papers = []

    ns = {"atom": "http://www.w3.org/2005/Atom"}

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
            "published_date": "",
            "arxiv_id": arxiv_id, 
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else "",
        })
    return papers