CREATE TABLE IF NOT EXISTS paper_chunks (
    chunk_id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    total_chunks INTEGER NOT NULL,
    page_start INTEGER,
    page_end INTEGER,
    content_type TEXT NOT NULL CHECK (content_type IN ('pdf', 'abstract')),
    ingestion_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(paper_id, ingestion_version, chunk_index, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_paper_chunks_paper_version
    ON paper_chunks(paper_id, ingestion_version, chunk_index);
