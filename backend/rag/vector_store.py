import chromadb
from chromadb.config import Settings as ChromaSettings
from backend.config import settings

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

def add_chunks(chunks: list[dict], embeddings: list[list[float]], paper_id: str):
    """put all chunks and  vectors of a paper into db

    Args: 
        chunks: chunk_paper() 's output: [{"conten":"...", "chunk_index": 0}, ...]
        embeddings: embed_texts() 's output: [[0.1, 0.2, ...], ...]
        paper_id: the source_id of a paper, such as "arxiv:2301.123456"
    """ 
    if not chunks:
        return
    
    collection = get_collection()

    collection.add(
        ids=[f"{paper_id}_chunk{i}" for i, c in enumerate(chunks)],
        documents=[c["content"] for c in chunks],
        embeddings=embeddings,
        metadatas=[{
            "paper_id": paper_id,
            "chunk_index": c["chunk_index"],
        } for c in chunks] ,
    )
    
def is_paper_indexed(paper_id: str) -> bool:
    """Check if a paper is already in the vector store."""
    collection = get_collection()
    try:
        result = collection.get(
            ids=[f"{paper_id}_chunk0"],
        )
        return len(result.get("ids", [])) > 0
    except Exception:
        return False


def search(query_embedding: list[float], n_results: int = 10) -> list[dict]:
    """use query vector to search the most relevant chunk

    Returns:
        [{"content": "...", "paper_id": "arxiv:...", "chunk_index": 3}, ...]
    """

    collection = get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    return [
        {"content": docs[i], "paper_id": metas[i]["paper_id"], "chunk_index": metas[i]["chunk_index"]}
        for i in range(len(docs))
    ]