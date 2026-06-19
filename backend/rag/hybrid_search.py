from rank_bm25 import BM25Okapi
from backend.rag.embeddings import embed_single
from backend.rag.vector_store import get_collection

_bm25_index = None
_bm25_chunks = []

def _get_bm25():
    """Build or return the BM25 index for all the stored chunks"""
    global _bm25_index, _bm25_chunks

    collections = get_collection()
    all_data = collections.get()

    # if data not change, then use cache
    current_count = len(all_data["documents"])
    if _bm25_index is not None and len(_bm25_chunks) == current_count:
        return _bm25_index, _bm25_chunks
    
    # build new bm25 index
    _bm25_chunks = all_data["documents"]
    tokenized = [doc.split() for doc in _bm25_chunks]
    _bm25_index = BM25Okapi(tokenized)
    return _bm25_index, _bm25_chunks

async def hybrid_search(query: str, n_results: int = 10) -> list[dict]:
    """Hybrid search: Semantics + BM25 → RRF fusion"""

    # 1.semantic search
    query_embedding = await embed_single(query)
    semantic_results = _semantic_search(query_embedding, n_results * 2)

    # 2.BM25 key word search
    bm25_results = _bm25_search(query,  n_results * 2)

    # 3.RRF 融合
    merged = _rrf_fusion(semantic_results, bm25_results, k=60)
    return merged[:n_results]

def _semantic_search(query_embedding: list[float], n: int) -> list[dict]:
    from backend.rag.vector_store import search
    return search(query_embedding, n_results=n)

def _bm25_search(query: str, n: int) -> list[dict]:
    """BM25 key word search"""
    bm25, chunks = _get_bm25()
    if bm25 is None:
        return []
    
    tokenized_query = query.split()
    scores = bm25.get_scores(tokenized_query)

    # top k
    indexed = sorted(enumerate(scores), key=lambda x:x[1], reverse=True)[:n]
    
    collection = get_collection()
    all_metas = collection.get()["metadatas"]

    return [
        {"content": chunks[i], "paper_id": all_metas[i]["paper_id"], "chunk_index":all_metas[i]["chunk_index"]}
        for i, _score in indexed
    ]

def _rrf_fusion(results_a: list[dict], results_b: list[dict], k: int = 60) -> list[dict]:
    """RRF(Reciprocal Rank Fusion) fuse two set of results"""
    scores = {}
    content_map = {}

    for rank, item in enumerate(results_a, 1):
        key = item["content"][:100]
        scores[key] = scores.get(key, 0) + 1 / (k + rank)
        content_map[key] = item
    
    for rank, item in enumerate(results_b, 1):
        key = item["content"][:100]
        scores[key] = scores.get(key, 0) + 1 / (k + rank)
        content_map[key] = item

    sorted_keys = sorted(scores, key=scores.get, reverse=True)
    return [content_map[key] for key in sorted_keys]