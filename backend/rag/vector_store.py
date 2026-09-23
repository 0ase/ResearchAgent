import chromadb
from chromadb.config import Settings as ChromaSettings
from backend.config import settings
from backend.domain.evidence import CURRENT_INGESTION_VERSION

_client = None

def _get_client():
    """Obtain or create a ChromaDB client (persisted to the hard disk)"""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
    return _client

def get_collection(name: str = "paper"):
    """obtain or create the collecction named paper"""
    client = _get_client()
    return client.get_or_create_collection(name=name)

def add_chunks(
    chunks: list[dict],
    embeddings: list[list[float]],
    paper_id: str,
    ingestion_version: str = CURRENT_INGESTION_VERSION,
):
    """put all chunks and vectors of a paper into db

    Args: 
        chunks: chunk_paper() 's output: [{"conten":"...", "chunk_index": 0}, ...]
        embeddings: embed_texts() 's output: [[0.1, 0.2, ...], ...]
        paper_id: the source_id of a paper, such as "arxiv:2301.123456"
    """ 
    if not chunks:
        return
    
    collection = get_collection()

    collection.upsert(
        ids=[c.get("chunk_id") or f"{paper_id}_chunk{i}" for i, c in enumerate(chunks)],
        documents=[c["content"] for c in chunks],
        embeddings=embeddings,
        metadatas=[{
            "paper_id": paper_id,
            "chunk_id": c.get("chunk_id") or f"{paper_id}_chunk{i}",
            "chunk_index": c["chunk_index"],
            "page_start": c.get("page_start") if c.get("page_start") is not None else -1,
            "page_end": c.get("page_end") if c.get("page_end") is not None else -1,
            "content_type": c.get("content_type", "pdf"),
            "ingestion_version": c.get("ingestion_version", ingestion_version),
        } for c in chunks] ,
    )
    
def is_paper_indexed(
    paper_id: str,
    ingestion_version: str = CURRENT_INGESTION_VERSION,
) -> bool:
    """Check whether the current version of a paper is already indexed."""
    collection = get_collection()
    try:
        result = collection.get(
            where={
                "$and": [
                    {"paper_id": paper_id},
                    {"ingestion_version": ingestion_version},
                ]
            },
        )
        return len(result.get("ids", [])) > 0
    except Exception:
        return False


def search(query_embedding: list[float], n_results: int = 10) -> list[dict]:
    """use query vector to search the most relevant chunk

    Returns:
        [{"content": "...", "paper_id": "arxiv:...", "chunk_id": "chunk:...", ...}, ...]
    """

    collection = get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    return [
        {
            "content": docs[i],
            "paper_id": metas[i]["paper_id"],
            "chunk_id": metas[i].get("chunk_id"),
            "chunk_index": metas[i]["chunk_index"],
            "page_start": _page_value(metas[i].get("page_start")),
            "page_end": _page_value(metas[i].get("page_end")),
            "content_type": metas[i].get("content_type", "pdf"),
            "ingestion_version": metas[i].get("ingestion_version"),
        }
        for i in range(len(docs))
    ]


def _page_value(value):
    return None if value in (None, -1) else value
