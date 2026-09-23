from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime, timezone

from backend.db.connection import open_database
from backend.domain.papers import PaperSnapshot, PaperSourceAlias
from backend.repositories import DatabaseFactory


class PaperRepository:
    def __init__(self, connection_factory: DatabaseFactory | None = None) -> None:
        self._connection_factory = connection_factory or open_database

    async def upsert_task_papers(
        self,
        task_id: str,
        papers: Iterable[PaperSnapshot | dict],
        *,
        preserve_existing: bool = False,
    ) -> list[PaperSnapshot]:
        database = await self._connection_factory()
        now = datetime.now(timezone.utc).isoformat()
        try:
            task_row = await self._fetch_one(
                database,
                "SELECT status FROM research_tasks WHERE id = ?",
                (task_id,),
            )
            task_is_terminal = bool(
                task_row and task_row["status"] in {"completed", "failed", "cancelled", "interrupted"}
            )

            for value in papers:
                paper = value if isinstance(value, PaperSnapshot) else PaperSnapshot.model_validate(value)
                if paper.task_id != task_id:
                    paper = paper.model_copy(update={"task_id": task_id})
                existing = await self._fetch_one(
                    database,
                    "SELECT * FROM research_papers WHERE task_id = ? AND canonical_id = ?",
                    (task_id, paper.canonical_id),
                )
                if existing is None:
                    existing = await self._find_by_aliases(database, task_id, paper.aliases)
                if existing is None:
                    await database.execute(
                        """
                        INSERT INTO research_papers(
                            id, task_id, canonical_id, title, authors_json, abstract,
                            year, citation_count, pdf_url, landing_page_url, doi,
                            source, source_id, selected, relevance_score,
                            relevance_reason, metadata_locked, full_text_status,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        _paper_values(paper, now, metadata_locked=task_is_terminal),
                    )
                    paper_id = paper.paper_id
                else:
                    paper_id = existing["id"]
                    locked = bool(existing["metadata_locked"]) or task_is_terminal
                    if existing["canonical_id"] != paper.canonical_id:
                        collision = await self._fetch_one(
                            database,
                            """
                            SELECT id FROM research_papers
                            WHERE task_id = ? AND canonical_id = ? AND id <> ?
                            """,
                            (task_id, paper.canonical_id, paper_id),
                        )
                        if collision is None:
                            await database.execute(
                                "UPDATE research_papers SET canonical_id = ? WHERE id = ?",
                                (paper.canonical_id, paper_id),
                            )
                    if not (preserve_existing or locked):
                        await database.execute(
                            """
                            UPDATE research_papers
                            SET title = COALESCE(NULLIF(?, ''), title),
                                authors_json = CASE WHEN ? = '[]' THEN authors_json ELSE ? END,
                                abstract = COALESCE(?, abstract),
                                year = COALESCE(?, year),
                                citation_count = COALESCE(?, citation_count),
                                pdf_url = COALESCE(?, pdf_url),
                                landing_page_url = COALESCE(?, landing_page_url),
                                doi = COALESCE(?, doi),
                                full_text_status = ?,
                                updated_at = ?
                            WHERE id = ?
                            """,
                            (
                                paper.title,
                                json.dumps(paper.authors, ensure_ascii=False),
                                json.dumps(paper.authors, ensure_ascii=False),
                                paper.abstract,
                                paper.year,
                                paper.citation_count,
                                paper.pdf_url,
                                paper.landing_page_url,
                                paper.doi,
                                paper.full_text_status,
                                now,
                                paper_id,
                            ),
                        )
                    if task_is_terminal and not existing["metadata_locked"]:
                        await database.execute(
                            "UPDATE research_papers SET metadata_locked = 1 WHERE id = ?",
                            (paper_id,),
                        )

                for alias in paper.aliases:
                    await database.execute(
                        """
                        INSERT INTO paper_source_aliases(
                            task_id, paper_id, source, source_id, landing_page_url
                        ) VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(task_id, source, source_id) DO UPDATE SET
                            landing_page_url = COALESCE(
                                paper_source_aliases.landing_page_url,
                                excluded.landing_page_url
                            ),
                            paper_id = excluded.paper_id
                        """,
                        (
                            task_id,
                            paper_id,
                            alias.source,
                            alias.source_id,
                            alias.landing_page_url,
                        ),
                    )
            await database.commit()
            return await self._list_for_task(database, task_id)
        finally:
            await database.close()

    async def list_for_task(self, task_id: str) -> list[PaperSnapshot]:
        database = await self._connection_factory()
        try:
            return await self._list_for_task(database, task_id)
        finally:
            await database.close()

    async def get(self, task_id: str, paper_id: str) -> PaperSnapshot | None:
        database = await self._connection_factory()
        try:
            row = await self._fetch_one(
                database,
                "SELECT * FROM research_papers WHERE task_id = ? AND id = ?",
                (task_id, paper_id),
            )
            return await self._row_to_paper(database, row) if row else None
        finally:
            await database.close()

    async def update_selection(
        self,
        task_id: str,
        paper_id: str,
        *,
        selected: bool,
        relevance_score: float | None,
        relevance_reason: str | None,
    ) -> PaperSnapshot | None:
        database = await self._connection_factory()
        try:
            cursor = await database.execute(
                """
                UPDATE research_papers
                SET selected = ?, relevance_score = ?, relevance_reason = ?, updated_at = ?
                WHERE task_id = ? AND id = ?
                """,
                (
                    int(selected),
                    relevance_score,
                    relevance_reason,
                    datetime.now(timezone.utc).isoformat(),
                    task_id,
                    paper_id,
                ),
            )
            await database.commit()
            if cursor.rowcount != 1:
                return None
            row = await self._fetch_one(
                database,
                "SELECT * FROM research_papers WHERE task_id = ? AND id = ?",
                (task_id, paper_id),
            )
            return await self._row_to_paper(database, row) if row else None
        finally:
            await database.close()

    async def lock_task_snapshot(self, task_id: str) -> None:
        database = await self._connection_factory()
        try:
            await database.execute(
                "UPDATE research_papers SET metadata_locked = 1 WHERE task_id = ?",
                (task_id,),
            )
            await database.commit()
        finally:
            await database.close()

    async def _list_for_task(self, database, task_id: str) -> list[PaperSnapshot]:
        cursor = await database.execute(
            "SELECT * FROM research_papers WHERE task_id = ? ORDER BY created_at ASC, id ASC",
            (task_id,),
        )
        return [await self._row_to_paper(database, row) for row in await cursor.fetchall()]

    async def _find_by_aliases(self, database, task_id: str, aliases: list[PaperSourceAlias]):
        for alias in aliases:
            row = await self._fetch_one(
                database,
                """
                SELECT p.*
                FROM research_papers AS p
                JOIN paper_source_aliases AS a ON a.paper_id = p.id AND a.task_id = p.task_id
                WHERE a.task_id = ? AND a.source = ? AND a.source_id = ?
                LIMIT 1
                """,
                (task_id, alias.source, alias.source_id),
            )
            if row is not None:
                return row
        return None

    async def _row_to_paper(self, database, row) -> PaperSnapshot:
        cursor = await database.execute(
            """
            SELECT source, source_id, landing_page_url
            FROM paper_source_aliases
            WHERE task_id = ? AND paper_id = ?
            ORDER BY id ASC
            """,
            (row["task_id"], row["id"]),
        )
        aliases = [
            PaperSourceAlias(
                source=alias["source"],
                source_id=alias["source_id"],
                landing_page_url=alias["landing_page_url"],
            )
            for alias in await cursor.fetchall()
        ]
        return PaperSnapshot(
            paper_id=row["id"],
            task_id=row["task_id"],
            canonical_id=row["canonical_id"],
            title=row["title"],
            authors=json.loads(row["authors_json"] or "[]"),
            abstract=row["abstract"],
            year=row["year"],
            citation_count=row["citation_count"],
            pdf_url=row["pdf_url"],
            landing_page_url=row["landing_page_url"],
            doi=row["doi"],
            source=row["source"],
            source_id=row["source_id"],
            selected=bool(row["selected"]),
            relevance_score=row["relevance_score"],
            relevance_reason=row["relevance_reason"],
            aliases=aliases,
            metadata_locked=bool(row["metadata_locked"]),
            full_text_status=row["full_text_status"],
        )

    @staticmethod
    async def _fetch_one(database, query: str, parameters: Iterable[object]):
        cursor = await database.execute(query, tuple(parameters))
        return await cursor.fetchone()


def _paper_values(paper: PaperSnapshot, now: str, *, metadata_locked: bool) -> tuple:
    return (
        paper.paper_id,
        paper.task_id,
        paper.canonical_id,
        paper.title,
        json.dumps(paper.authors, ensure_ascii=False),
        paper.abstract,
        paper.year,
        paper.citation_count,
        paper.pdf_url,
        paper.landing_page_url,
        paper.doi,
        paper.source,
        paper.source_id,
        int(paper.selected),
        paper.relevance_score,
        paper.relevance_reason,
        int(metadata_locked or paper.metadata_locked),
        paper.full_text_status,
        now,
        now,
    )
