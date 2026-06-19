import fitz

def extract_text_from_pdf(pdf_path: str) -> str:
    """use PyMuPDF extract pure text from pdf"""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def chunk_text(text: str, chunk_size: int = 512, overlap: int = 128) -> list[str]:
    """cut the long range text into smaller block, each block has overlap"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

def chunk_paper(pdf_path: str) -> list[dict]:
    """the full process of chunking a paper"""
    full_text = extract_text_from_pdf(pdf_path)
    text_chunks = chunk_text(full_text)

    result = []
    for i, chunk in enumerate(text_chunks):
        if len(chunk.strip()) < 50:
            continue
        result.append({
            "content": chunk,
            "chunk_index": i,
            "total_chunks": len(text_chunks),
        })
    return result 