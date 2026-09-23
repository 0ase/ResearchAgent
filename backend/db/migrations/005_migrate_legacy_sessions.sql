CREATE TABLE IF NOT EXISTS legacy_session_migrations (
    session_id TEXT PRIMARY KEY,
    migrated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
