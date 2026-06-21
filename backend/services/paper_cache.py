import os
from pathlib import Path
import httpx
from backend.config import settings

async def download_pdf(paper: dict) -> str | None:
    """download a PDF of the paper, return the path of the file"""

    # confirm the name of file and the cache path
    cache_dir = Path(settings.paper_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    source_id = paper.get("source_id", "unknown").replace(":", "_")
    filepath = cache_dir / f"{source_id}.pdf"

    if filepath.exists():
        return str(filepath)
    
    pdf_url = paper.get("pdf_url", "")
    if not pdf_url:
        doi = paper.get("doi", "")
        if doi:
            pdf_url = await _resolve_doi_to_pdf(doi)
        if not pdf_url:
            return None
    try:
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(pdf_url)
            resp.raise_for_status()
            filepath.write_bytes(resp.content)
            return str(filepath)
    except Exception:
        return None

async def _resolve_doi_to_pdf(doi: str) -> str | None:
    """use Unpaywall api to search OA pdf url"""
    email = settings.unpaywall_email
    url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
    client_kwargs = {"timeout": 15}
    if settings.http_proxy:
        client_kwargs["proxy"] = settings.http_proxy
    try:
        async with httpx.AsyncClient(**client_kwargs) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            best = data.get("best_oa_location") or {}
            pdf_url = best.get("url_for_pdf") if isinstance(best, dict) else None
            if pdf_url:
                print(f"    [Unpaywall] {doi[:40]} ... -> pdf found")
            return pdf_url
    except Exception as e:
        print(f"    [Unpaywall] {doi[:40]} ... -> {type(e).__name__}")
        return None