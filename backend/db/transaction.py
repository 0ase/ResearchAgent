"""Reuse repository methods in one service-owned transaction."""
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class Transaction:
    factory: object
    database: object
    notifications: dict = field(default_factory=dict)
    aborted: bool = False


_current: ContextVar[Transaction | None] = ContextVar("repository_transaction", default=None)


class BorrowedConnection:
    def __init__(self, tx):
        self.tx = tx

    def __getattr__(self, name):
        return getattr(self.tx.database, name)

    async def execute(self, sql, *args, **kwargs):
        if sql.strip().upper().startswith("BEGIN"):
            return await self.tx.database.execute("SELECT 1")
        return await self.tx.database.execute(sql, *args, **kwargs)

    async def commit(self):
        pass

    async def close(self):
        pass

    async def rollback(self):
        self.tx.aborted = True


async def repository_connection(factory):
    tx = _current.get()
    if tx is not None:
        if tx.factory is not factory:
            raise RuntimeError("Repositories in a transaction must share a database factory")
        return BorrowedConnection(tx)
    return await factory()


def defer_notification(key, callback):
    tx = _current.get()
    if tx is None:
        return False
    tx.notifications[key] = callback
    return True


@asynccontextmanager
async def transaction(factory):
    if _current.get() is not None:
        raise RuntimeError("Nested lifecycle transactions are not supported")
    database = await factory()
    tx = Transaction(factory, database)
    token = _current.set(tx)
    committed = False
    try:
        await database.execute("BEGIN IMMEDIATE")
        yield
        if tx.aborted:
            raise RuntimeError("A repository aborted the transaction")
        await database.commit()
        committed = True
    except BaseException:
        await database.rollback()
        raise
    finally:
        _current.reset(token)
        await database.close()
    if committed:
        for callback in tx.notifications.values():
            await callback()
