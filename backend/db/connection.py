from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import aiosqlite

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
    database_path = resolve_database_path(settings_or_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    database = await aiosqlite.connect(database_path)
    database.row_factory = aiosqlite.Row
    await database.execute("PRAGMA journal_mode = WAL")
    await database.execute("PRAGMA foreign_keys = ON")
    await database.execute("PRAGMA busy_timeout = 5000")
    return database
