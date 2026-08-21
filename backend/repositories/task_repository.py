from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from datetime import datetime, timezone

from backend.api.schemas.tasks import (
    StageSnapshot,
    TaskProgress,
    TaskSnapshot,
    TaskStatus,
)
from backend.db.connection import open_database
from backend.domain.tasks import effective_locale_for_task, is_terminal, transition_task
from backend.repositories import DatabaseFactory


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _progress_payload(task: TaskSnapshot) -> dict:
    return {
        "message": task.progress.message,
        "metrics": task.progress.metrics,
        "stages": [stage.model_dump(mode="json") for stage in task.stages],
        "statistics": task.statistics,
    }


def _row_to_task(row) -> TaskSnapshot:
    payload = json.loads(row["progress_json"] or "{}")
    options = json.loads(row["options_json"] or "{}")
    stages = [StageSnapshot.model_validate(item) for item in payload.get("stages", [])]
    status = TaskStatus(row["status"])
    return TaskSnapshot(
        id=row["id"],
        parent_task_id=row["parent_task_id"],
        client_request_id=row["client_request_id"],
        query=row["query"],
        title=row["title"],
        status=status,
        effective_locale=effective_locale_for_task(
            row["query"],
            options.get("output_language"),
        ),
        current_stage=row["current_stage"],
        options=options,
        progress=TaskProgress(
            message=payload.get("message"),
            metrics=payload.get("metrics", {}),
        ),
        stages=stages,
        statistics=payload.get("statistics", {}),
        last_sequence=0,
        available_actions=_available_actions(status),
        created_at=_parse_datetime(row["created_at"]),
        started_at=_parse_datetime(row["started_at"]),
        completed_at=_parse_datetime(row["completed_at"]),
        error_code=row["error_code"],
        error_message=row["error_message"],
    )


def _available_actions(status: TaskStatus) -> list[str]:
    if status in {TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.CANCELLING}:
        return ["cancel"] if status is not TaskStatus.CANCELLING else []
    return ["retry", "rename", "delete"]


class TaskRepository:
    def __init__(self, connection_factory: DatabaseFactory | None = None) -> None:
        self._connection_factory = connection_factory or open_database

    async def create(self, task: TaskSnapshot) -> TaskSnapshot:
        database = await self._connection_factory()
        try:
            existing = await self._fetch_one(
                database,
                "SELECT * FROM research_tasks WHERE client_request_id = ?",
                (task.client_request_id,),
            )
            if existing is not None:
                return _row_to_task(existing)

            await database.execute(
                """
                INSERT INTO research_tasks(
                    id, parent_task_id, client_request_id, query, title, status,
                    current_stage, options_json, progress_json, error_code,
                    error_message, created_at, started_at, completed_at,
                    cancel_requested_at, deleted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.parent_task_id,
                    task.client_request_id,
                    task.query,
                    task.title,
                    task.status.value,
                    task.current_stage.value if task.current_stage else None,
                    json.dumps(task.options, ensure_ascii=False),
                    json.dumps(_progress_payload(task), ensure_ascii=False),
                    task.error_code,
                    task.error_message,
                    _serialize_datetime(task.created_at),
                    _serialize_datetime(task.started_at),
                    _serialize_datetime(task.completed_at),
                    None,
                    None,
                ),
            )
            await database.commit()
            return task
        except sqlite3.IntegrityError:
            await database.rollback()
            existing = await self._fetch_one(
                database,
                "SELECT * FROM research_tasks WHERE client_request_id = ?",
                (task.client_request_id,),
            )
            if existing is not None:
                return _row_to_task(existing)
            raise
        finally:
            await database.close()

    async def get(self, task_id: str) -> TaskSnapshot | None:
        database = await self._connection_factory()
        try:
            row = await self._fetch_one(
                database,
                """
                SELECT * FROM research_tasks
                WHERE id = ? AND deleted_at IS NULL
                """,
                (task_id,),
            )
            return _row_to_task(row) if row else None
        finally:
            await database.close()

    async def get_by_client_request_id(self, client_request_id: str) -> TaskSnapshot | None:
        database = await self._connection_factory()
        try:
            row = await self._fetch_one(
                database,
                """
                SELECT * FROM research_tasks
                WHERE client_request_id = ? AND deleted_at IS NULL
                """,
                (client_request_id,),
            )
            return _row_to_task(row) if row else None
        finally:
            await database.close()

    async def get_active(self) -> TaskSnapshot | None:
        database = await self._connection_factory()
        try:
            row = await self._fetch_one(
                database,
                """
                SELECT * FROM research_tasks
                WHERE deleted_at IS NULL
                  AND status IN ('queued', 'running', 'cancelling')
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (),
            )
            return _row_to_task(row) if row else None
        finally:
            await database.close()

    async def transition_status(
        self,
        task_id: str,
        *,
        expected_status: TaskStatus,
        target_status: TaskStatus,
        current_stage: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> TaskSnapshot | None:
        transition_task(expected_status, target_status)
        database = await self._connection_factory()
        now = datetime.now(timezone.utc)
        try:
            values: list[object] = [target_status.value]
            assignments = ["status = ?"]
            if current_stage is not None:
                assignments.append("current_stage = ?")
                values.append(current_stage)
            if target_status is TaskStatus.RUNNING:
                assignments.append("started_at = COALESCE(started_at, ?)")
                values.append(_serialize_datetime(now))
            if target_status is TaskStatus.CANCELLING:
                assignments.append("cancel_requested_at = ?")
                values.append(_serialize_datetime(now))
            if is_terminal(target_status):
                assignments.append("completed_at = COALESCE(completed_at, ?)")
                values.append(_serialize_datetime(now))
            if error_code is not None:
                assignments.append("error_code = ?")
                values.append(error_code)
            if error_message is not None:
                assignments.append("error_message = ?")
                values.append(error_message)

            values.extend([task_id, expected_status.value])
            cursor = await database.execute(
                f"""
                UPDATE research_tasks
                SET {', '.join(assignments)}
                WHERE id = ? AND status = ? AND deleted_at IS NULL
                """,
                tuple(values),
            )
            await database.commit()
            if cursor.rowcount != 1:
                return None
            row = await self._fetch_one(
                database,
                "SELECT * FROM research_tasks WHERE id = ?",
                (task_id,),
            )
            return _row_to_task(row) if row else None
        finally:
            await database.close()

    async def list_history(self, limit: int = 20) -> list[TaskSnapshot]:
        database = await self._connection_factory()
        try:
            cursor = await database.execute(
                """
                SELECT * FROM research_tasks
                WHERE deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (max(1, min(limit, 100)),),
            )
            rows = await cursor.fetchall()
            return [_row_to_task(row) for row in rows]
        finally:
            await database.close()

    async def soft_delete(self, task_id: str) -> bool:
        database = await self._connection_factory()
        try:
            cursor = await database.execute(
                """
                UPDATE research_tasks
                SET deleted_at = ?
                WHERE id = ?
                  AND status IN ('completed', 'failed', 'cancelled', 'interrupted')
                  AND deleted_at IS NULL
                """,
                (datetime.now(timezone.utc).isoformat(), task_id),
            )
            await database.commit()
            return cursor.rowcount == 1
        finally:
            await database.close()

    async def update_title(self, task_id: str, title: str) -> TaskSnapshot | None:
        database = await self._connection_factory()
        try:
            cursor = await database.execute(
                """
                UPDATE research_tasks
                SET title = ?
                WHERE id = ? AND deleted_at IS NULL
                """,
                (title, task_id),
            )
            await database.commit()
            if cursor.rowcount != 1:
                return None
            row = await self._fetch_one(
                database,
                "SELECT * FROM research_tasks WHERE id = ?",
                (task_id,),
            )
            return _row_to_task(row) if row else None
        finally:
            await database.close()

    async def update_statistics(
        self,
        task_id: str,
        statistics: dict,
    ) -> TaskSnapshot | None:
        """Persist result-derived statistics in the task snapshot."""
        database = await self._connection_factory()
        try:
            row = await self._fetch_one(
                database,
                "SELECT progress_json FROM research_tasks WHERE id = ? AND deleted_at IS NULL",
                (task_id,),
            )
            if row is None:
                return None
            payload = json.loads(row["progress_json"] or "{}")
            payload["statistics"] = statistics
            cursor = await database.execute(
                "UPDATE research_tasks SET progress_json = ? WHERE id = ? AND deleted_at IS NULL",
                (json.dumps(payload, ensure_ascii=False), task_id),
            )
            await database.commit()
            if cursor.rowcount != 1:
                return None
            updated = await self._fetch_one(
                database,
                "SELECT * FROM research_tasks WHERE id = ?",
                (task_id,),
            )
            return _row_to_task(updated) if updated else None
        finally:
            await database.close()

    async def mark_active_interrupted(self) -> list[str]:
        database = await self._connection_factory()
        now = datetime.now(timezone.utc).isoformat()
        try:
            cursor = await database.execute(
                """
                SELECT id FROM research_tasks
                WHERE status IN ('queued', 'running', 'cancelling')
                  AND deleted_at IS NULL
                """
            )
            task_ids = [row[0] for row in await cursor.fetchall()]
            if task_ids:
                await database.execute(
                    """
                    UPDATE research_tasks
                    SET status = 'interrupted',
                        completed_at = COALESCE(completed_at, ?),
                        error_code = 'TASK_INTERRUPTED',
                        error_message = '服务重启导致任务中断'
                    WHERE status IN ('queued', 'running', 'cancelling')
                      AND deleted_at IS NULL
                    """,
                    (now,),
                )
                await database.commit()
            return task_ids
        finally:
            await database.close()

    @staticmethod
    async def _fetch_one(database, query: str, parameters: Iterable[object]):
        cursor = await database.execute(query, tuple(parameters))
        return await cursor.fetchone()
