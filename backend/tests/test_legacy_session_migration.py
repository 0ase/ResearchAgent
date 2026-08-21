import json
import pathlib
import sqlite3

import pytest

from backend.config import Settings
from backend.db.connection import open_database
from backend.db.migrate import migrate_database
from backend.repositories.result_repository import ResultRepository
from backend.repositories.task_repository import TaskRepository


@pytest.mark.asyncio
async def test_legacy_sessions_migrate_once_without_replay_or_evidence(tmp_path) -> None:
    settings = Settings(_env_file=None, database_path=str(tmp_path / "research.db"))
    pathlib.Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.database_path)
    connection.execute(
        """
        CREATE TABLE sessions (
            session_id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            created_at TEXT NOT NULL,
            papers_count INTEGER DEFAULT 0,
            score TEXT DEFAULT '',
            result_json TEXT DEFAULT '{}'
        )
        """
    )
    connection.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)",
        (
            "legacy-1",
            "legacy query",
            "2026-01-01T00:00:00+00:00",
            2,
            "8",
            json.dumps({"final_answer": "# Legacy report", "papers": []}),
        ),
    )
    connection.commit()
    connection.close()

    assert await migrate_database(settings) == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert await migrate_database(settings) == []

    factory = lambda: open_database(settings)
    task = await TaskRepository(factory).get("legacy-1")
    result = await ResultRepository(factory).get("legacy-1")

    assert task is not None
    assert task.status.value == "completed"
    assert result is not None
    assert result.report_markdown == "# Legacy report"
    assert result.capabilities.supports_replay is False
    assert result.capabilities.supports_evidence is False
