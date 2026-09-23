from __future__ import annotations

from pathlib import Path
import os
from typing import TYPE_CHECKING

import aiosqlite
import asyncio

from backend.config import settings as default_settings

if TYPE_CHECKING:
    from backend.config import Settings


def resolve_database_path(settings_or_path: Settings | str | Path | None = None) -> Path:
    if settings_or_path is None:
        return Path(default_settings.database_path)
    if isinstance(settings_or_path, (str, Path)):
        return Path(settings_or_path)
    return Path(settings_or_path.database_path)


async def open_database(
    settings_or_path: Settings | str | Path | None = None,
) -> aiosqlite.Connection:
    """Open a configured SQLite connection with the required safety pragmas."""
    database_path = validate_database_path(settings_or_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = asyncio.ensure_future(aiosqlite.connect(database_path))
    try:
        database = await asyncio.shield(connection)
    except asyncio.CancelledError:
        database = await connection
        await database.close()
        raise
    try:
        database.row_factory = aiosqlite.Row
        await database.execute("PRAGMA journal_mode = WAL")
        await database.execute("PRAGMA foreign_keys = ON")
        await database.execute("PRAGMA busy_timeout = 5000")
        return database
    except BaseException:
        await database.close()
        raise


def validate_database_path(settings_or_path=None) -> Path:
    database_path = resolve_database_path(settings_or_path).resolve()
    test_root = os.environ.get("RESEARCH_TEST_ROOT")
    if test_root and not database_path.is_relative_to(Path(test_root).resolve()):
        raise RuntimeError("Test database path is outside the isolated test root")
    return database_path
