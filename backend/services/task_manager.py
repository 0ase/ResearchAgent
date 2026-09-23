from __future__ import annotations

import asyncio
import uuid
import logging
import sqlite3
from contextlib import asynccontextmanager

from backend.db.transaction import transaction
from backend.config import current_settings
from datetime import datetime, timezone

from backend.api.schemas.events import EventType
from backend.api.schemas.tasks import (
    CreateResearchTaskRequest,
    ResearchTaskOptions,
    TaskSnapshot,
    TaskStatus,
)
from backend.domain.tasks import effective_locale_for_task, is_terminal
from backend.domain.errors import ResearchPipelineError, PIPELINE_ERROR_MESSAGES
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
        configuration=None,
    ) -> None:
        self.tasks = task_repository
        self.events = event_repository
        self.results = result_repository
        self.evidence = evidence_repository
        self.configuration = configuration or current_settings()
        self.runner = runner or TaskRunner(event_recorder=event_repository, configuration=self.configuration)
        self._lock = asyncio.Lock()
        self._runner_task: asyncio.Task | None = None
        self._cancel_event: asyncio.Event | None = None
        self._observers: set[asyncio.Task] = set()
        self._closing = False
        self.storage_failed = False

    async def create_task(self, request: CreateResearchTaskRequest) -> TaskSnapshot:
        try:
            async with self._lock:
                return await self._create_task_locked(request)
        except (OSError, sqlite3.Error) as exc:
            self._storage_error(exc)
            raise

    async def retry_task(self, task_id: str) -> TaskSnapshot:
        async with self._lock, self._storage_guard():
            original = await self.tasks.get(task_id)
            if original is None:
                raise TaskNotFoundError(task_id)
            if not is_terminal(original.status):
                raise ActiveTaskError(original)
            legacy_options = dict(original.options)
            if "max_papers" in legacy_options:
                legacy_options["max_papers"] = max(3, min(15, int(legacy_options["max_papers"])))
            options = ResearchTaskOptions.model_validate(legacy_options)
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
        if self.storage_failed or self._closing:
            raise RuntimeError("STORAGE_UNAVAILABLE")
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
        async with transaction(self.tasks._connection_factory):
            task = await self.tasks.create(task)
            await self.events.append(task_id=task.id, event_type=EventType.TASK_CREATED,
                                     payload={"query": task.query, "title": task.title})
        cancel_event = asyncio.Event()
        self._cancel_event = cancel_event
        invocation = self._execute(task, cancel_event)
        try:
            self._runner_task = asyncio.create_task(invocation, name=f"research-task-{task.id}")
        except BaseException:
            invocation.close()
            await self._terminal_locked(task.id, TaskStatus.FAILED, "INTERNAL_ERROR")
            raise
        self._runner_task.add_done_callback(lambda future: self._observe(task.id, future))
        return task

    def _observe(self, task_id, future):
        # Observe every exception, including failures before Runner.run starts.
        if not future.cancelled():
            error = future.exception()
            if error:
                logging.getLogger(__name__).error("Research worker escaped: %s", type(error).__name__)
        observer = asyncio.create_task(self._ensure_terminal(task_id))
        self._observers.add(observer)
        observer.add_done_callback(self._observers.discard)

    async def _ensure_terminal(self, task_id):
        try:
            await self._finish(task_id, TaskStatus.INTERRUPTED if self._closing else TaskStatus.FAILED,
                               "TASK_INTERRUPTED" if self._closing else "INTERNAL_ERROR")
        except Exception as exc:
            self._storage_error(exc)

    def _storage_error(self, exc):
        self.storage_failed = True
        logging.getLogger(__name__).error("Task storage unavailable: %s", type(exc).__name__)

    @asynccontextmanager
    async def _storage_guard(self):
        try:
            yield
        except (OSError, sqlite3.Error) as exc:
            self._storage_error(exc)
            raise

    async def cancel_task(self, task_id: str) -> TaskSnapshot:
        async with self._lock, self._storage_guard():
            async with transaction(self.tasks._connection_factory):
                task = await self.tasks.get(task_id)
                if task is None:
                    raise TaskNotFoundError(task_id)
                if is_terminal(task.status):
                    return task
                if task.status is not TaskStatus.CANCELLING:
                    updated = await self.tasks.transition_status(task_id, expected_status=task.status,
                                                                 target_status=TaskStatus.CANCELLING)
                    if updated is not None:
                        task = updated
                        await self.events.append(task_id=task_id,
                            event_type=EventType.TASK_CANCELLATION_REQUESTED, payload={})
            if self._cancel_event is not None:
                self._cancel_event.set()
            return task

    async def recover_interrupted_tasks(self) -> list[str]:
        async with self._lock:
            async with transaction(self.tasks._connection_factory):
                task_ids = await self.tasks.mark_active_interrupted()
                for task_id in task_ids:
                    await self.events.append(task_id=task_id, event_type=EventType.TASK_INTERRUPTED,
                                             payload={"code": "TASK_INTERRUPTED"})
            return task_ids

    async def wait_for_current_task(self) -> None:
        current = self._runner_task
        if current is not None:
            await asyncio.gather(current, return_exceptions=True)
        await asyncio.sleep(0)
        if self._observers:
            await asyncio.gather(*list(self._observers), return_exceptions=True)

    async def shutdown(self) -> None:
        self._closing = True
        current = self._runner_task
        if current is not None and not current.done():
            current.cancel()
        await self.wait_for_current_task()
        await self.recover_interrupted_tasks()

    async def _execute(self, task: TaskSnapshot, cancel_event: asyncio.Event) -> None:
        try:
            async with self._lock:
                async with transaction(self.tasks._connection_factory):
                    running = await self.tasks.transition_status(task.id,
                        expected_status=TaskStatus.QUEUED, target_status=TaskStatus.RUNNING)
                    if running is not None:
                        await self.events.append(task_id=task.id, event_type=EventType.TASK_STARTED, payload={})
            if running is None:
                if cancel_event.is_set():
                    await self._finish_cancelled(task.id)
                return
            state = await self.runner.run(running, cancel_event)
            if cancel_event.is_set():
                await self._finish_cancelled(task.id)
                return
            replay = bool(await self.events.list_events_after(task.id, after_sequence=0))
            result = build_result(task.id, state, supports_replay=replay)
            validate_result_ready(result)
            async with self._lock:
                async with transaction(self.tasks._connection_factory):
                    current = await self.tasks.get(task.id)
                    if current is None or current.status is not TaskStatus.RUNNING or cancel_event.is_set():
                        result = None
                    else:
                        updated = await self.tasks.transition_status(task.id,
                            expected_status=TaskStatus.RUNNING, target_status=TaskStatus.COMPLETED)
                        if updated is None:
                            return
                        if self.evidence is not None and (result.citations or result.evidence):
                            await self.evidence.save_result_evidence(task.id, result.citations, result.evidence)
                        await self.results.upsert(result)
                        await self.tasks.update_statistics(task.id, result.statistics)
                        await self.events.append(task_id=task.id, event_type=EventType.RESULT_AVAILABLE,
                                                 payload={"partial": result.partial})
                        await self.events.append(task_id=task.id, event_type=EventType.TASK_COMPLETED, payload={})
            if result is None and cancel_event.is_set():
                await self._finish_cancelled(task.id)
        except asyncio.CancelledError:
            if cancel_event.is_set():
                await self._finish_cancelled(task.id)
            else:
                await self._finish(task.id, TaskStatus.INTERRUPTED, "TASK_INTERRUPTED")
        except Exception as exc:
            code = exc.code if isinstance(exc, ResearchPipelineError) else "INTERNAL_ERROR"
            try:
                if cancel_event.is_set():
                    await self._finish_cancelled(task.id)
                else:
                    await self._finish(task.id, TaskStatus.FAILED, code)
            except Exception as storage_exc:
                self._storage_error(storage_exc)
        finally:
            async with self._lock:
                if self._runner_task is asyncio.current_task():
                    self._runner_task = None
                    self._cancel_event = None

    async def _terminal_locked(self, task_id, status, code=None):
        async with transaction(self.tasks._connection_factory):
            current = await self.tasks.get(task_id)
            if current is None or is_terminal(current.status):
                return
            updated = await self.tasks.transition_status(task_id, expected_status=current.status,
                target_status=status, error_code=code,
                error_message=PIPELINE_ERROR_MESSAGES.get(code, "研究任务执行失败") if status is TaskStatus.FAILED else None)
            if updated is not None:
                event = {TaskStatus.FAILED: EventType.TASK_FAILED,
                         TaskStatus.CANCELLED: EventType.TASK_CANCELLED,
                         TaskStatus.INTERRUPTED: EventType.TASK_INTERRUPTED}[status]
                await self.events.append(task_id=task_id, event_type=event,
                                         payload={"code": code} if code else {})

    async def _finish(self, task_id, status, code=None):
        async with self._lock:
            await self._terminal_locked(task_id, status, code)

    async def _finish_cancelled(self, task_id: str) -> None:
        await self._finish(task_id, TaskStatus.CANCELLED)


def _title_from_query(query: str) -> str:
    title = query.splitlines()[0].strip()
    return title[:80] or "New research task"
