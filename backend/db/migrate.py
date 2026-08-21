from __future__ import annotations

import json
from pathlib import Path

import aiosqlite

from backend.db.connection import open_database

MIGRATIONS_DIR = Path(__file__).with_name("migrations")


def _migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


async def _ensure_schema_migrations_table(database: aiosqlite.Connection) -> None:
    await database.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await database.commit()


async def migrate_database(settings_or_path=None) -> list[int]:
    """Apply pending SQL migrations and return their numeric versions."""
    database = await open_database(settings_or_path)
    applied_versions: list[int] = []
    try:
        await _ensure_schema_migrations_table(database)
        rows = await database.execute_fetchall(
            "SELECT version FROM schema_migrations ORDER BY version"
        )
        applied = {row[0] for row in rows}

        for migration_file in _migration_files():
            version = int(migration_file.name.split("_", maxsplit=1)[0])
            if version in applied:
                continue

            sql = migration_file.read_text(encoding="utf-8")
            await database.execute("BEGIN")
            try:
                # The project migrations are deliberately DDL-only. Splitting
                # on semicolons keeps each file inside an explicit transaction.
                for statement in sql.split(";"):
                    statement = statement.strip()
                    if statement:
                        await database.execute(statement)
                if version == 5:
                    await _migrate_legacy_sessions(database)
                await database.execute(
                    "INSERT INTO schema_migrations(version, name) VALUES (?, ?)",
                    (version, migration_file.name),
                )
                await database.commit()
            except Exception:
                await database.rollback()
                raise
            applied_versions.append(version)

        return applied_versions
    finally:
        await database.close()


async def _migrate_legacy_sessions(database: aiosqlite.Connection) -> None:
    cursor = await database.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'sessions'"
    )
    table = await cursor.fetchone()
    if table is None:
        return

    rows = await database.execute_fetchall("SELECT * FROM sessions")
    for row in rows:
        session_id, query, created_at, papers_count, score, result_json = row
        marker_cursor = await database.execute(
            "SELECT 1 FROM legacy_session_migrations WHERE session_id = ?",
            (session_id,),
        )
        marker = await marker_cursor.fetchone()
        if marker is not None:
            continue
        result = json.loads(result_json or "{}")
        critique = result.get("critique") or {}
        progress = {
            "statistics": {
                "papers_count": papers_count or 0,
                "score": score or critique.get("score", ""),
            }
        }
        await database.execute(
            """
            INSERT OR IGNORE INTO research_tasks(
                id, client_request_id, query, title, status, current_stage,
                options_json, progress_json, created_at, completed_at
            ) VALUES (?, ?, ?, ?, 'completed', 'critic', '{}', ?, ?, ?)
            """,
            (
                session_id,
                f"legacy:{session_id}",
                query,
                query[:80] or "Legacy research task",
                json.dumps(progress, ensure_ascii=False),
                created_at,
                created_at,
            ),
        )
        await database.execute(
            """
            INSERT OR IGNORE INTO research_results(
                task_id, report_markdown, analysis_json, critique_json,
                statistics_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                result.get("final_answer", ""),
                json.dumps(result.get("analysis", {}) or {}, ensure_ascii=False),
                json.dumps(critique, ensure_ascii=False),
                json.dumps(
                    {
                        "papers": result.get("papers", []) or [],
                        "paper_insights": result.get("paper_insights", []) or [],
                        "statistics": {
                            "papers_count": papers_count or 0,
                            "score": score or critique.get("score", ""),
                        },
                        "capabilities": {
                            "supports_replay": False,
                            "supports_evidence": False,
                            "supports_structured_papers": False,
                        },
                    },
                    ensure_ascii=False,
                ),
                created_at,
                created_at,
            ),
        )
        await database.execute(
            "INSERT INTO legacy_session_migrations(session_id) VALUES (?)",
            (session_id,),
        )
