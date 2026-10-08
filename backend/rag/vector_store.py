import logging
from backend.core.observability import report_exception
from backend.core.errors import VectorStoreUnavailable
from backend.rag.vector_runtime import get_worker


class CollectionProxy:
    def __init__(self, name: str):
        self.name = name

    def get(self, **kwargs):
        return get_worker().call(self.name, "get", **kwargs)

    def query(self, **kwargs):
        return get_worker().call(self.name, "query", **kwargs)

    def add(self, **kwargs):
        return get_worker().call(self.name, "add", **kwargs)

    def count(self):
        return get_worker().call(self.name, "count")

def get_collection(name: str = "paper"):
    """Return a handle; native operations execute in the isolated worker."""
    return CollectionProxy(name)

def add_chunks(chunks: list[dict], embeddings: list[list[float]], paper_id: str):
    """put all chunks and vectors of a paper into db

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
    except VectorStoreUnavailable:
        raise
    except Exception as exc:
        report_exception(exc, "vector_store.lookup.failed", level=logging.WARNING, paper_id=paper_id)
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
