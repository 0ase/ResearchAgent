CREATE TABLE research_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES research_tasks(id),
    message_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    citations_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    UNIQUE(task_id, message_id, role)
);
CREATE TABLE followup_jobs (
    task_id TEXT PRIMARY KEY REFERENCES research_tasks(id),
    message_id TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('queued','processing','failed')),
    error_code TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE followup_requests (
    task_id TEXT NOT NULL REFERENCES research_tasks(id),
    message_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    PRIMARY KEY(task_id, message_id)
);
CREATE INDEX idx_research_messages_task ON research_messages(task_id,id);
