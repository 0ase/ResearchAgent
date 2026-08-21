import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.db.connection import open_database
from backend.db.migrate import migrate_database
import backend.main as main_module


@pytest.mark.asyncio
async def test_migrations_create_nested_data_directory(tmp_path) -> None:
    database_path = tmp_path / "nested" / "research.db"
    settings = Settings(_env_file=None, database_path=str(database_path))

    applied = await migrate_database(settings)

    assert database_path.exists()
    assert applied == [1, 2, 3, 4, 5, 6, 7, 8, 9]


@pytest.mark.asyncio
async def test_migrations_are_idempotent_and_record_versions(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        database_path=str(tmp_path / "research.db"),
    )

    first = await migrate_database(settings)
    second = await migrate_database(settings)

    assert first == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert second == []

    connection = sqlite3.connect(settings.database_path)
    try:
        rows = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
    finally:
        connection.close()
    assert rows == [(1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,), (9,)]


@pytest.mark.asyncio
async def test_database_pragmas_and_schema_constraints_exist(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        database_path=str(tmp_path / "research.db"),
    )
    await migrate_database(settings)

    database = await open_database(settings)
    try:
        journal_mode = (await (await database.execute("PRAGMA journal_mode")).fetchone())[0]
        foreign_keys = (await (await database.execute("PRAGMA foreign_keys")).fetchone())[0]
        busy_timeout = (await (await database.execute("PRAGMA busy_timeout")).fetchone())[0]
        table_names = {
            row[0]
            for row in await (
                await database.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            ).fetchall()
        }
        task_indexes = {
            row[1]
            for row in await (
                await database.execute("PRAGMA index_list(research_tasks)")
            ).fetchall()
        }
        event_indexes = {
            row[1]
            for row in await (
                await database.execute("PRAGMA index_list(task_events)")
            ).fetchall()
        }
    finally:
        await database.close()

    assert journal_mode.lower() == "wal"
    assert foreign_keys == 1
    assert busy_timeout == 5000
    assert {"schema_migrations", "research_tasks", "task_events", "research_results"} <= table_names
    assert "idx_research_tasks_client_request_id" in task_indexes
    assert "idx_task_events_task_sequence" in event_indexes


def test_application_lifespan_runs_migrations(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "lifespan" / "research.db"
    monkeypatch.setattr(main_module.settings, "database_path", str(database_path))

    with TestClient(main_module.create_app()):
        pass

    assert database_path.exists()
