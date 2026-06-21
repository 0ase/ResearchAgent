import asyncio
import httpx
import xml.etree.ElementTree as ET

_pubmed_sem = asyncio.Semaphore(2)
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


async def search_pubmed(query: str, max_results: int = 10, timeout: int = 30) -> list[dict]:
    """use pubmed api to search papers"""
    async with _pubmed_sem:
        search_url = f"{BASE_URL}/esearch.fcgi"
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "xml",
            "sort": "relevance",
        }

        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.get(search_url, params=params)
                    resp.raise_for_status()
                    ids = _parse_id_list(resp.text)

                    if not ids:
                        return []

                    fetch_url = f"{BASE_URL}/efetch.fcgi"
                    fetch_param = {
                        "db": "pubmed",
                        "id": ",".join(ids),
                        "retmode": "xml",
                        "rettype": "abstract",
                    }
                    resp2 = await client.get(fetch_url, params=fetch_param)
                    resp2.raise_for_status()
                    return _parse_pubmed_response(resp2.text)
            except httpx.TimeoutException:
                if attempt == 0:
                    print(f"    [pubmed] timeout ({timeout}s), retrying...")
                    await asyncio.sleep(2)
                    continue
                print(f"    [pubmed] timeout after retry, giving up")
            except Exception as e:
                if attempt == 0:
                    await asyncio.sleep(2)
                    continue
                print(f"    [pubmed] error: {type(e).__name__}: {e}")

        return []


def _parse_id_list(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    return [id_elem.text for id_elem in root.findall(".//Id") if id_elem.text]


def _parse_pubmed_response(xml_text: str) -> list[dict]:
    """Parse the XML details of the paper returned by efetch"""
    root = ET.fromstring(xml_text)
    papers = []

    for article in root.findall(".//PubmedArticle"):
        # title
        title_elem = article.find(".//ArticleTitle")
        title = title_elem.text if title_elem is not None and title_elem.text else "Untitled"

        # abstract
        abstract_parts = []
        for abs_elem in article.findall(".//AbstractText"):
            if abs_elem.text:
                label = abs_elem.get("Label", "")
                prefix = f"{label}: " if label else ""
                abstract_parts.append(prefix + abs_elem.text)
        abstract = "".join(abstract_parts)

        # Authors
        authors = []
        for author in article.findall(".//Author"):
            last = author.find("./LastName")
            fore = author.find("./ForeName")
            if last is not None and last.text:
                name = last.text
                if fore is not None and fore.text:
                    name = f"{fore.text} {name}"
                authors.append(name)

        # PMID
        pmid_elem = article.find(".//PMID")
        pmid = pmid_elem.text if pmid_elem is not None and pmid_elem.text else ""

        # doi
        doi = ""
        for eid in article.findall(".//ELocationID"):
            if eid.get("EIdType") == "doi" and eid.text:
                doi = eid.text
        
        # pmc id (for full-text PDF)
        pmc_id = ""
        for aid in article.findall(".//ArticleId"):
            if aid.get("IdType") == "pmc" and aid.text:
                pmc_id = aid.text
                if not pmc_id.upper().startswith("PMC"):
                    pmc_id = "PMC" + pmc_id
                break

        papers.append({
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "source": "pubmed",
            "source_id": f"pubmed:{pmid}",
            "published_date": "",
            "doi": doi,
            "citation_count": 0,
            "pdf_url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/" if pmc_id else "",
        })
    return papers
