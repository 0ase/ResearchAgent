from backend.services.paper_cache import download_pdf
from backend.services.chunking import chunk_paper
from backend.rag.embeddings import embed_texts
from backend.rag.vector_store import add_chunks, is_paper_indexed

async def ingest_paper(paper: dict) -> bool:
    """Complete paper archiving process: download → chunking → embedding → storing in vector database 

    Return: True - Success, False - Failure
    """

    paper_id = paper.get("source_id", "unknown")

    # 已在向量库中 → 跳过，秒返回
    if is_paper_indexed(paper_id):
        return True

    pdf_path = await download_pdf(paper)
    if pdf_path:
        chunks = chunk_paper(pdf_path)
        if not chunks:
            return False
    else:
        title = paper.get("title", "").strip()
        abstract = paper.get("abstract", "").strip()
        if not title and not abstract:
            return False
        content = (
            f"[Abstract-only -- no full text available]\n\n"
            f"Title: {title}\n"
            f"Abstract: {abstract}"
        )
        chunks = [{
            "content": content,
            "chunk_index": 0,
            "total_chunks": 1,
        }]
    
    texts = [c["content"] for c in chunks]
    embeddings = await embed_texts(texts)
    add_chunks(chunks, embeddings, paper_id)
    return True

async def ingest_papers(papers: list[dict]) -> int:
    """Batch import of multiple papers, return the number of successful operations"""
    count = 0
    for paper in papers:
        success = await ingest_paper(paper)
        if success:
            count += 1
    return count