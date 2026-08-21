CREATE TABLE IF NOT EXISTS report_citations (
    citation_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES research_tasks(id) ON DELETE CASCADE,
    section_id TEXT NOT NULL,
    paper_id TEXT,
    claim_ids_json TEXT NOT NULL DEFAULT '[]',
    display_number INTEGER,
    support_type TEXT NOT NULL DEFAULT 'unverified',
    valid INTEGER NOT NULL DEFAULT 0,
    validation_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_report_citations_task
    ON report_citations(task_id, display_number);

CREATE TABLE IF NOT EXISTS paper_evidence (
    evidence_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES research_tasks(id) ON DELETE CASCADE,
    paper_id TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    claim_id TEXT,
    excerpt TEXT NOT NULL,
    content_type TEXT NOT NULL CHECK (content_type IN ('pdf', 'abstract')),
    page_start INTEGER,
    page_end INTEGER,
    support_type TEXT NOT NULL DEFAULT 'unverified',
    verified INTEGER NOT NULL DEFAULT 0,
    validation_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_paper_evidence_task
    ON paper_evidence(task_id, paper_id, chunk_id);

CREATE TABLE IF NOT EXISTS citation_evidence (
    citation_id TEXT NOT NULL REFERENCES report_citations(citation_id) ON DELETE CASCADE,
    evidence_id TEXT NOT NULL REFERENCES paper_evidence(evidence_id) ON DELETE CASCADE,
    rank INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(citation_id, evidence_id)
);
