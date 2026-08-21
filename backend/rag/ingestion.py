from dataclasses import dataclass, field

from backend.services.paper_cache import download_pdf
from backend.services.chunking import abstract_chunk, chunk_paper
from backend.rag.embeddings import embed_texts
from backend.rag.vector_store import add_chunks
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

    pdf_path = await download_pdf(paper)
    if pdf_path:
        chunks = chunk_paper(pdf_path, paper_id=paper_id)
        if not chunks:
            return IngestionResult(
                paper_id=paper_id,
                readable=False,
                warnings=["PAPER_NO_READABLE_CONTENT"],
            )
    else:
        title = paper.get("title", "").strip()
        abstract = paper.get("abstract", "").strip()
        fallback = abstract_chunk(
            paper_id=paper_id,
            title=title,
            abstract=abstract,
        )
        if fallback is None:
            return IngestionResult(
                paper_id=paper_id,
                readable=False,
                warnings=["PAPER_NO_READABLE_CONTENT"],
            )
        chunks = [fallback]

    await repository.upsert_chunks(paper_id, chunks)
    warnings: list[str] = []
    vector_indexed = False
    if not settings.dashscope_api_key:
        warnings.append("EMBEDDING_NOT_CONFIGURED")
    else:
        try:
            texts = [c["content"] for c in chunks]
            embeddings = await embed_texts(texts)
            add_chunks(chunks, embeddings, paper_id)
            vector_indexed = True
        except Exception as exc:
            print(f"    [Ingestion] vector index skipped for {paper_id}: {type(exc).__name__}")
            warnings.append("EMBEDDING_FAILED")

    return IngestionResult(
        paper_id=paper_id,
        readable=True,
        chunk_count=len(chunks),
        vector_indexed=vector_indexed,
        warnings=warnings,
    )

async def ingest_papers(papers: list[dict]) -> int:
    """Batch import of multiple papers, return the number of successful operations"""
    count = 0
    for paper in papers:
        result = await ingest_paper(paper)
        if result.readable:
            count += 1
    return count
