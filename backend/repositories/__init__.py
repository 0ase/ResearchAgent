"""Persistence adapters for task, event, and result records."""

from collections.abc import Awaitable, Callable

import aiosqlite

DatabaseFactory = Callable[[], Awaitable[aiosqlite.Connection]]
