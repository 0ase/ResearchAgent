CREATE TABLE IF NOT EXISTS research_tasks (
    id TEXT PRIMARY KEY,
    parent_task_id TEXT REFERENCES research_tasks(id),
    client_request_id TEXT NOT NULL,
    query TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'queued', 'running', 'cancelling', 'completed',
            'failed', 'cancelled', 'interrupted'
        )
    ),
    current_stage TEXT,
    options_json TEXT NOT NULL DEFAULT '{}',
    progress_json TEXT NOT NULL DEFAULT '{}',
    error_code TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    cancel_requested_at TEXT,
    deleted_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_research_tasks_client_request_id
    ON research_tasks(client_request_id);

CREATE INDEX IF NOT EXISTS idx_research_tasks_status
    ON research_tasks(status);

CREATE INDEX IF NOT EXISTS idx_research_tasks_created_at
    ON research_tasks(created_at DESC);
