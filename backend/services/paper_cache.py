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
        return None
    
    try:
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(pdf_url)
            resp.raise_for_status()
            filepath.write_bytes(resp.content)
            return str(filepath)
    except Exception:
        return None