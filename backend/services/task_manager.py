from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from backend.api.schemas.events import EventType
from backend.api.schemas.tasks import (
    CreateResearchTaskRequest,
    ResearchTaskOptions,
    TaskSnapshot,
    TaskStatus,
)
from backend.domain.tasks import effective_locale_for_task, is_terminal
from backend.domain.errors import ResearchPipelineError
from backend.repositories.event_repository import EventRepository
from backend.repositories.evidence_repository import EvidenceRepository
from backend.repositories.result_repository import ResultRepository
from backend.repositories.task_repository import TaskRepository
from backend.services.task_runner import TaskRunner
from backend.services.result_builder import build_result, validate_result_ready


class ActiveTaskError(Exception):
    def __init__(self, task: TaskSnapshot) -> None:
        super().__init__("an active research task already exists")
        self.task = task


class TaskNotFoundError(Exception):
    pass


class TaskManager:
    def __init__(
        self,
        task_repository: TaskRepository,
        event_repository: EventRepository,
        result_repository: ResultRepository,
        *,
        runner: TaskRunner | object | None = None,
        evidence_repository: EvidenceRepository | None = None,
    ) -> None:
        self.tasks = task_repository
        self.events = event_repository
        self.results = result_repository
        self.evidence = evidence_repository
        self.runner = runner or TaskRunner(event_recorder=event_repository)
        self._lock = asyncio.Lock()
        self._runner_task: asyncio.Task | None = None
        self._cancel_event: asyncio.Event | None = None

    async def create_task(self, request: CreateResearchTaskRequest) -> TaskSnapshot:
        async with self._lock:
            return await self._create_task_locked(request)

    async def retry_task(self, task_id: str) -> TaskSnapshot:
        async with self._lock:
            original = await self.tasks.get(task_id)
            if original is None:
                raise TaskNotFoundError(task_id)
            if not is_terminal(original.status):
                raise ActiveTaskError(original)
            options = ResearchTaskOptions.model_validate(original.options)
            request = CreateResearchTaskRequest(
                client_request_id=str(uuid.uuid4()),
                query=original.query,
                options=options,
            )
            return await self._create_task_locked(request, parent_task_id=original.id)

    async def get_task(self, task_id: str) -> TaskSnapshot | None:
        return await self.tasks.get(task_id)

    async def rename_task(self, task_id: str, title: str) -> TaskSnapshot:
        updated = await self.tasks.update_title(task_id, title)
        if updated is None:
            raise TaskNotFoundError(task_id)
        return updated

    async def delete_task(self, task_id: str) -> None:
        task = await self.tasks.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        if not is_terminal(task.status):
            raise ActiveTaskError(task)
        if not await self.tasks.soft_delete(task_id):
            raise TaskNotFoundError(task_id)

    async def _create_task_locked(
        self,
        request: CreateResearchTaskRequest,
        *,
        parent_task_id: str | None = None,
    ) -> TaskSnapshot:
        existing = await self.tasks.get_by_client_request_id(request.client_request_id)
        if existing is not None:
            return existing

        active = await self.tasks.get_active()
        if active is not None:
            raise ActiveTaskError(active)

        now = datetime.now(timezone.utc)
        task = TaskSnapshot(
            id=str(uuid.uuid4()),
            parent_task_id=parent_task_id,
            client_request_id=request.client_request_id,
            query=request.query,
            title=_title_from_query(request.query),
            status=TaskStatus.QUEUED,
            effective_locale=effective_locale_for_task(
                request.query,
                request.options.output_language,
            ),
            options=request.options.model_dump(mode="json"),
            available_actions=["cancel"],
            created_at=now,
        )
        task = await self.tasks.create(task)
        await self.events.append(
            task_id=task.id,
            event_type=EventType.TASK_CREATED,
            payload={"query": task.query, "title": task.title},
        )

        cancel_event = asyncio.Event()
        self._cancel_event = cancel_event
        self._runner_task = asyncio.create_task(
            self._execute(task, cancel_event),
            name=f"research-task-{task.id}",
        )
        return task

    async def cancel_task(self, task_id: str) -> TaskSnapshot:
        async with self._lock:
            cancelling = None
            task = None
            for _ in range(2):
                task = await self.tasks.get(task_id)
                if task is None:
                    raise TaskNotFoundError(task_id)
                if is_terminal(task.status):
                    return task
                if task.status is TaskStatus.CANCELLING:
                    if self._cancel_event is not None:
                        self._cancel_event.set()
                    return task
                cancelling = await self.tasks.transition_status(
                    task_id,
                    expected_status=task.status,
                    target_status=TaskStatus.CANCELLING,
                )
                if cancelling is not None:
                    break
            if cancelling is None:
                raise TaskNotFoundError(task_id)
            if self._cancel_event is not None:
                self._cancel_event.set()
            await self.events.append(
                task_id=task_id,
                event_type=EventType.TASK_CANCELLATION_REQUESTED,
                payload={},
            )
            return cancelling

    async def recover_interrupted_tasks(self) -> list[str]:
        task_ids = await self.tasks.mark_active_interrupted()
        for task_id in task_ids:
            await self.events.append(
                task_id=task_id,
                event_type=EventType.TASK_INTERRUPTED,
                payload={"code": "TASK_INTERRUPTED"},
            )
        return task_ids

    async def wait_for_current_task(self) -> None:
        current = self._runner_task
        if current is not None:
            await asyncio.gather(current, return_exceptions=True)

    async def shutdown(self) -> None:
        current = self._runner_task
        if current is not None and not current.done():
            current.cancel()
            await asyncio.gather(current, return_exceptions=True)
        await self.recover_interrupted_tasks()

    async def _execute(
        self,
        task: TaskSnapshot,
        cancel_event: asyncio.Event,
    ) -> None:
        try:
            running = await self.tasks.transition_status(
                task.id,
                expected_status=TaskStatus.QUEUED,
                target_status=TaskStatus.RUNNING,
            )
            if running is None:
                if cancel_event.is_set():
                    await self._finish_cancelled(task.id)
                return

            await self.events.append(
                task_id=task.id,
                event_type=EventType.TASK_STARTED,
                payload={},
            )
            try:
                state = await self.runner.run(running, cancel_event)
                replay_capable = bool(
                    await self.events.list_events_after(task.id, after_sequence=0)
                )
                result = build_result(
                    task.id,
                    state,
                    supports_replay=replay_capable,
                )
                validate_result_ready(result)
                if self.evidence is not None and (result.citations or result.evidence):
                    await self.evidence.save_result_evidence(
                        task.id,
                        result.citations,
                        result.evidence,
                    )
                await self.results.upsert(result)
                await self.tasks.update_statistics(task.id, result.statistics)
                await self.events.append(
                    task_id=task.id,
                    event_type=EventType.RESULT_AVAILABLE,
                    payload={"partial": result.partial},
                )
            except asyncio.CancelledError:
                if cancel_event.is_set():
                    await self._finish_cancelled(task.id)
                    return
                raise
            except ResearchPipelineError as exc:
                if cancel_event.is_set():
                    await self._finish_cancelled(task.id)
                else:
                    await self.tasks.transition_status(
                        task.id,
                        expected_status=TaskStatus.RUNNING,
                        target_status=TaskStatus.FAILED,
                        error_code=exc.code,
                        error_message=exc.public_message,
                    )
                    await self.events.append(
                        task_id=task.id,
                        event_type=EventType.TASK_FAILED,
                        payload={"code": exc.code},
                    )
                return
            except Exception:
                if cancel_event.is_set():
                    await self._finish_cancelled(task.id)
                else:
                    await self.tasks.transition_status(
                        task.id,
                        expected_status=TaskStatus.RUNNING,
                        target_status=TaskStatus.FAILED,
                        error_code="INTERNAL_ERROR",
                        error_message="研究任务执行失败",
                    )
                    await self.events.append(
                        task_id=task.id,
                        event_type=EventType.TASK_FAILED,
                        payload={"code": "INTERNAL_ERROR"},
                    )
                return

            if cancel_event.is_set():
                await self._finish_cancelled(task.id)
            else:
                await self.tasks.transition_status(
                    task.id,
                    expected_status=TaskStatus.RUNNING,
                    target_status=TaskStatus.COMPLETED,
                )
                await self.events.append(
                    task_id=task.id,
                    event_type=EventType.TASK_COMPLETED,
                    payload={},
                )
        finally:
            async with self._lock:
                if self._runner_task is asyncio.current_task():
                    self._runner_task = None
                    self._cancel_event = None

    async def _finish_cancelled(self, task_id: str) -> None:
        current = await self.tasks.get(task_id)
        if current is None or is_terminal(current.status):
            return
        await self.tasks.transition_status(
            task_id,
            expected_status=current.status,
            target_status=TaskStatus.CANCELLED,
        )
        await self.events.append(
            task_id=task_id,
            event_type=EventType.TASK_CANCELLED,
            payload={},
        )


def _title_from_query(query: str) -> str:
    title = query.splitlines()[0].strip()
    return title[:80] or "New research task"
