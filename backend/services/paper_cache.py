import hashlib
from pathlib import Path

import httpx

from backend.config import settings

MAX_PDF_BYTES = 50 * 1024 * 1024


def _is_pdf(content: bytes) -> bool:
    return content.lstrip().startswith(b"%PDF")

async def download_pdf(paper: dict) -> str | None:
    """download a PDF of the paper, return the path of the file"""

    # confirm the name of file and the cache path
    cache_dir = Path(settings.paper_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_key = str(
        paper.get("source_id")
        or paper.get("doi")
        or paper.get("pdf_url")
        or paper.get("title")
        or "unknown"
    )
    safe_id = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
    filepath = cache_dir / f"{safe_id}.pdf"

    if filepath.exists():
        try:
            if _is_pdf(filepath.read_bytes()[:16]):
                return str(filepath)
        except OSError:
            pass
    
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
            content = resp.content
            if not content or len(content) > MAX_PDF_BYTES or not _is_pdf(content[:16]):
                return None
            filepath.write_bytes(content)
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
