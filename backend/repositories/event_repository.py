from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from backend.api.schemas.events import EventLevel, EventType, ResearchEvent
from backend.api.schemas.tasks import ResearchStage
from backend.db.connection import open_database
from backend.repositories import DatabaseFactory


def _event_from_row(row) -> ResearchEvent:
    return ResearchEvent(
        schema_version=row["schema_version"],
        task_id=row["task_id"],
        sequence=row["sequence"],
        event_type=row["event_type"],
        stage=row["stage"],
        level=row["level"],
        payload=json.loads(row["payload_json"] or "{}"),
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
    )


class EventRepository:
    def __init__(self, connection_factory: DatabaseFactory | None = None) -> None:
        self._connection_factory = connection_factory or open_database

    async def append(
        self,
        *,
        task_id: str,
        event_type: EventType,
        stage: ResearchStage | None = None,
        level: EventLevel = EventLevel.INFO,
        payload: dict[str, Any] | None = None,
        schema_version: int = 1,
        occurred_at: datetime | None = None,
    ) -> ResearchEvent:
        database = await self._connection_factory()
        occurred_at = occurred_at or datetime.now(timezone.utc)
        try:
            await database.execute("BEGIN IMMEDIATE")
            cursor = await database.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM task_events WHERE task_id = ?",
                (task_id,),
            )
            sequence = (await cursor.fetchone())[0]
            await database.execute(
                """
                INSERT INTO task_events(
                    task_id, sequence, schema_version, event_type, stage,
                    level, payload_json, occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    sequence,
                    schema_version,
                    event_type.value,
                    stage.value if stage else None,
                    level.value,
                    json.dumps(payload or {}, ensure_ascii=False),
                    occurred_at.isoformat(),
                ),
            )
            await database.commit()
            return ResearchEvent(
                schema_version=schema_version,
                task_id=task_id,
                sequence=sequence,
                event_type=event_type,
                stage=stage,
                level=level,
                payload=payload or {},
                occurred_at=occurred_at,
            )
        except Exception:
            await database.rollback()
            raise
        finally:
            await database.close()

    async def list_events_after(
        self,
        task_id: str,
        after_sequence: int = 0,
    ) -> list[ResearchEvent]:
        database = await self._connection_factory()
        try:
            cursor = await database.execute(
                """
                SELECT * FROM task_events
                WHERE task_id = ? AND sequence > ?
                ORDER BY sequence ASC
                """,
                (task_id, after_sequence),
            )
            return [_event_from_row(row) for row in await cursor.fetchall()]
        finally:
            await database.close()

    async def latest_sequence(self, task_id: str) -> int:
        database = await self._connection_factory()
        try:
            cursor = await database.execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM task_events WHERE task_id = ?",
                (task_id,),
            )
            return (await cursor.fetchone())[0]
        finally:
            await database.close()
