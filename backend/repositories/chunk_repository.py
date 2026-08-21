from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime, timezone

from backend.db.connection import open_database
from backend.domain.evidence import CURRENT_INGESTION_VERSION, PaperChunk
from backend.repositories import DatabaseFactory


class ChunkRepository:
    def __init__(self, connection_factory: DatabaseFactory | None = None) -> None:
        self._connection_factory = connection_factory or open_database

    async def upsert_chunks(
        self,
        paper_id: str,
        chunks: Iterable[PaperChunk | dict],
    ) -> list[PaperChunk]:
        database = await self._connection_factory()
        now = datetime.now(timezone.utc).isoformat()
        try:
            for value in chunks:
                chunk = value if isinstance(value, PaperChunk) else PaperChunk.model_validate(value)
                await database.execute(
                    """
                    INSERT INTO paper_chunks(
                        chunk_id, paper_id, content, content_hash, chunk_index,
                        total_chunks, page_start, page_end, content_type,
                        ingestion_version, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(chunk_id) DO UPDATE SET
                        content = excluded.content,
                        content_hash = excluded.content_hash,
                        chunk_index = excluded.chunk_index,
                        total_chunks = excluded.total_chunks,
                        page_start = excluded.page_start,
                        page_end = excluded.page_end,
                        content_type = excluded.content_type,
                        ingestion_version = excluded.ingestion_version,
                        updated_at = excluded.updated_at
                    """,
                    (
                        chunk.chunk_id,
                        paper_id,
                        chunk.content,
                        chunk.content_hash,
                        chunk.chunk_index,
                        chunk.total_chunks,
                        chunk.page_start,
                        chunk.page_end,
                        chunk.content_type,
                        chunk.ingestion_version,
                        now,
                        now,
                    ),
                )
            await database.commit()
            return await self.list_for_paper(
                paper_id,
                connection=database,
            )
        finally:
            await database.close()

    async def list_for_paper(
        self,
        paper_id: str,
        ingestion_version: str | None = None,
        *,
        connection=None,
    ) -> list[PaperChunk]:
        database = connection or await self._connection_factory()
        try:
            if ingestion_version is None:
                cursor = await database.execute(
                    """
                    SELECT * FROM paper_chunks
                    WHERE paper_id = ?
                    ORDER BY ingestion_version DESC, chunk_index ASC
                    """,
                    (paper_id,),
                )
            else:
                cursor = await database.execute(
                    """
                    SELECT * FROM paper_chunks
                    WHERE paper_id = ? AND ingestion_version = ?
                    ORDER BY chunk_index ASC
                    """,
                    (paper_id, ingestion_version),
                )
            return [_row_to_chunk(row) for row in await cursor.fetchall()]
        finally:
            if connection is None:
                await database.close()

    async def get(self, chunk_id: str) -> PaperChunk | None:
        database = await self._connection_factory()
        try:
            cursor = await database.execute(
                "SELECT * FROM paper_chunks WHERE chunk_id = ?",
                (chunk_id,),
            )
            row = await cursor.fetchone()
            return _row_to_chunk(row) if row else None
        finally:
            await database.close()


def _row_to_chunk(row) -> PaperChunk:
    return PaperChunk(
        chunk_id=row["chunk_id"],
        paper_id=row["paper_id"],
        content=row["content"],
        content_hash=row["content_hash"],
        chunk_index=row["chunk_index"],
        total_chunks=row["total_chunks"],
        page_start=row["page_start"],
        page_end=row["page_end"],
        content_type=row["content_type"],
        ingestion_version=row["ingestion_version"],
    )
