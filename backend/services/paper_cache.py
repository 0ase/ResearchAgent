import hashlib
from pathlib import Path

import httpx

from backend.config import settings

MAX_PDF_BYTES = 50 * 1024 * 1024


def _is_pdf(content: bytes) -> bool:
    return content.lstrip().startswith(b"%PDF")

async def download_pdf(paper: dict) -> str | None:
    """Bound the entire lookup/download, never buffer a complete response."""
    import asyncio
    import uuid
    from backend.services.blocking_worker import file_io
    from backend.services.provider_retry import request_with_retry

    cache_dir = Path(settings.paper_cache_dir)
    cache_key = str(paper.get("source_id") or paper.get("doi") or paper.get("pdf_url") or paper.get("title") or "unknown")
    filepath = cache_dir / (hashlib.sha256(cache_key.encode()).hexdigest() + ".pdf")
    temporary = filepath.with_suffix(f".{uuid.uuid4().hex}.part")
    handle = None
    try:
        async with asyncio.timeout(settings.download_timeout):
            await file_io(lambda: cache_dir.mkdir(parents=True, exist_ok=True))
            def valid_cached():
                if not filepath.exists() or filepath.stat().st_size > MAX_PDF_BYTES:
                    return False
                with filepath.open("rb") as cached:
                    return _is_pdf(cached.read(16))
            if await file_io(valid_cached):
                return str(filepath)
            pdf_url = paper.get("pdf_url")
            if not pdf_url and paper.get("doi"):
                pdf_url = await _resolve_doi_to_pdf(paper["doi"])
            if not pdf_url:
                return None
            timeout = httpx.Timeout(settings.download_idle_timeout, connect=settings.download_connect_timeout)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                async def transfer():
                    nonlocal handle
                    count = 0
                    header = bytearray()
                    async with client.stream("GET", pdf_url) as response:
                        response.raise_for_status()
                        if int(response.headers.get("content-length", "0")) > MAX_PDF_BYTES:
                            raise ValueError("PDF_TOO_LARGE")
                        handle = await file_io(temporary.open, "wb")
                        try:
                            async for block in response.aiter_bytes(chunk_size=65536):
                                count += len(block)
                                if count > MAX_PDF_BYTES:
                                    raise ValueError("PDF_TOO_LARGE")
                                if len(header) < 16:
                                    header.extend(block[:16-len(header)])
                                await file_io(handle.write, block)
                        finally:
                            await file_io(handle.close)
                            handle = None
                    if not count or not _is_pdf(bytes(header)):
                        raise ValueError("INVALID_PDF")
                await request_with_retry(transfer)
            await file_io(temporary.replace, filepath)
            return str(filepath)
    except asyncio.CancelledError:
        raise
    except Exception:
        return None
    finally:
        if handle is not None:
            await file_io(handle.close)
        await file_io(lambda: temporary.unlink(missing_ok=True))

async def _resolve_doi_to_pdf(doi: str) -> str | None:
    """use Unpaywall api to search OA pdf url"""
    email = settings.unpaywall_email
    url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
    client_kwargs = {"timeout": httpx.Timeout(settings.download_idle_timeout, connect=settings.download_connect_timeout)}
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
