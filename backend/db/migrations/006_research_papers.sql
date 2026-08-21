CREATE TABLE IF NOT EXISTS research_papers (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES research_tasks(id) ON DELETE CASCADE,
    canonical_id TEXT NOT NULL,
    title TEXT NOT NULL,
    authors_json TEXT NOT NULL DEFAULT '[]',
    abstract TEXT,
    year INTEGER,
    citation_count INTEGER,
    pdf_url TEXT,
    landing_page_url TEXT,
    doi TEXT,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    selected INTEGER NOT NULL DEFAULT 0,
    relevance_score REAL,
    relevance_reason TEXT,
    metadata_locked INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(task_id, canonical_id)
);

CREATE INDEX IF NOT EXISTS idx_research_papers_task_id
    ON research_papers(task_id, created_at);

CREATE TABLE IF NOT EXISTS paper_source_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES research_tasks(id) ON DELETE CASCADE,
    paper_id TEXT NOT NULL REFERENCES research_papers(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    landing_page_url TEXT,
    UNIQUE(task_id, source, source_id)
);

CREATE INDEX IF NOT EXISTS idx_paper_source_aliases_paper_id
    ON paper_source_aliases(paper_id);
