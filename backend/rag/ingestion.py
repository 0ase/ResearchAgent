import asyncio
from dataclasses import dataclass, field

from backend.services.paper_cache import download_pdf
from backend.services.chunking import abstract_chunk, chunk_paper
from backend.rag.embeddings import embed_texts
from backend.services.blocking_worker import run_blocking_worker
from backend.config import settings
from backend.domain.evidence import CURRENT_INGESTION_VERSION
from backend.repositories.chunk_repository import ChunkRepository


@dataclass(slots=True)
class IngestionResult:
    paper_id: str
    readable: bool
    chunk_count: int = 0
    vector_indexed: bool = False
    warnings: list[str] = field(default_factory=list)


async def ingest_paper(
    paper: dict,
    *,
    chunk_repository: ChunkRepository | None = None,
    index_vectors: bool = True,
    parse_semaphore=None,
) -> IngestionResult:
    """Persist readable paper chunks and optionally create a vector index."""

    paper_id = paper.get("paper_id") or paper.get("id") or paper.get("source_id", "unknown")

    repository = chunk_repository or ChunkRepository()
    list_for_paper = getattr(repository, "list_for_paper", None)
    if list_for_paper is not None:
        existing_chunks = await list_for_paper(paper_id, CURRENT_INGESTION_VERSION)
        if existing_chunks:
            return IngestionResult(
                paper_id=paper_id,
                readable=True,
                chunk_count=len(existing_chunks),
            )

    warnings: list[str] = []
    pdf_path = await download_pdf(paper)
    chunks = []
    if pdf_path:
        try:
            async with parse_semaphore or asyncio.Semaphore(1):
                chunks = await run_blocking_worker("pdf", {
                    "path": pdf_path, "paper_id": paper_id, "chunk_size": settings.chunk_size,
                    "chunk_overlap": settings.chunk_overlap,
                }, settings.pdf_parse_timeout)
        except asyncio.CancelledError:
            raise
        except Exception:
            warnings.append("PDF_PARSE_FAILED")
    if not chunks:
        fallback = abstract_chunk(paper_id=paper_id, title=paper.get("title", "").strip(),
                                  abstract=paper.get("abstract", "").strip())
        if fallback is None:
            return IngestionResult(paper_id=paper_id, readable=False,
                                   warnings=[*warnings, "PAPER_NO_READABLE_CONTENT"])
        chunks = [fallback]
        warnings.append("ABSTRACT_ONLY")

    await repository.upsert_chunks(paper_id, chunks)
    vector_indexed = False
    if index_vectors:
        index_warnings = await index_paper_chunks(paper_id, chunks)
        warnings.extend(index_warnings)
        vector_indexed = not index_warnings
    return IngestionResult(paper_id=paper_id, readable=True, chunk_count=len(chunks),
                           vector_indexed=vector_indexed, warnings=warnings)


async def index_paper_chunks(paper_id, chunks):
    if not settings.dashscope_api_key:
        return ["EMBEDDING_NOT_CONFIGURED"]
    try:
        embeddings = await embed_texts([c["content"] for c in chunks])
        await run_blocking_worker("vector", {"paper_id": paper_id, "chunks": chunks,
            "embeddings": embeddings, "directory": str(settings.chroma_persist_dir)}, settings.vector_timeout)
        return []
    except asyncio.CancelledError:
        raise
    except Exception:
        return ["EMBEDDING_FAILED"]


async def ingest_papers(papers: list[dict]) -> int:
    """Batch import of multiple papers, return the number of successful operations"""
    count = 0
    for paper in papers:
        result = await ingest_paper(paper)
        if result.readable:
            count += 1
    return count
