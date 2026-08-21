CREATE TABLE IF NOT EXISTS research_results (
    task_id TEXT PRIMARY KEY REFERENCES research_tasks(id) ON DELETE CASCADE,
    report_markdown TEXT NOT NULL DEFAULT '',
    analysis_json TEXT NOT NULL DEFAULT '{}',
    critique_json TEXT NOT NULL DEFAULT '{}',
    statistics_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
