from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.errors import install_error_handlers
from backend.api.routes_events import router as events_router
from backend.api.routes_exports import router as exports_router
from backend.api.routes_history import router as history_router
from backend.api.routes_research import router as research_router
from backend.api.routes_settings import router as settings_router
from backend.api.routes_tasks import router as tasks_router
from backend.api.routes_followup import router as followup_router
from backend.repositories.followup_repository import FollowUpRepository
from backend.services.followup_manager import FollowUpManager
from backend.config import PROJECT_ENV_PATH, Settings, current_settings, settings, settings_scope
from backend.db.connection import open_database
from backend.db.migrate import migrate_database
from backend.db.runtime_lock import DatabaseRuntimeLock
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from pydantic.json_schema import models_json_schema
from backend.api.schemas.events import ResearchEvent
from backend.repositories.event_repository import EventRepository
from backend.repositories.evidence_repository import EvidenceRepository
from backend.repositories.result_repository import ResultRepository
from backend.repositories.task_repository import TaskRepository
from backend.services.event_recorder import EventRecorder
from backend.services.demo_task_runner import DemoTaskRunner
from backend.services.deepseek_settings import DeepSeekSettingsService
from backend.services.task_manager import TaskManager


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Initialize durable storage before serving requests."""
    with settings_scope(application.state.configuration):
        with DatabaseRuntimeLock(application.state.configuration.database_path):
            async with runtime_lifespan(application):
                yield


@asynccontextmanager
async def runtime_lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = application.state.configuration
    await migrate_database(settings)
    database_factory = lambda: open_database(settings)
    event_recorder = EventRecorder(EventRepository(database_factory))
    runner = application.state.injected_runner
    if settings.research_runner_mode == "demo" and runner is None:
        if settings.environment == "production":
            raise RuntimeError("RESEARCH_RUNNER_MODE=demo is not allowed in production")
        runner = DemoTaskRunner(
            event_recorder=event_recorder,
            delay_seconds=settings.demo_delay_seconds,
        )
    manager = TaskManager(
        TaskRepository(database_factory),
        event_recorder,
        ResultRepository(database_factory),
        runner=runner,
        evidence_repository=EvidenceRepository(database_factory),
        configuration=settings,
    )
    application.state.task_manager = manager
    application.state.event_recorder = event_recorder
    application.state.deepseek_settings_service = DeepSeekSettingsService(
        settings,
        application.state.env_path,
    )
    await manager.recover_interrupted_tasks()
    followup = FollowUpManager(FollowUpRepository(database_factory), manager.tasks, manager.results,
                              answerer=application.state.injected_answerer, configuration=settings)
    application.state.followup_manager = followup
    try:
        await followup.start()
        yield
    finally:
        try:
            await followup.shutdown()
        finally:
            await manager.shutdown()


def create_app(configuration: Settings | None = None, *, env_path: Path | None = None,
               runner=None, answerer=None) -> FastAPI:
    settings = configuration or current_settings()
    application = FastAPI(
        title="多Agent学术研究助手",
        version=settings.api_version,
        lifespan=lifespan,
    )
    application.state.configuration = settings
    application.state.env_path = env_path or Path(settings.model_config.get("env_file") or PROJECT_ENV_PATH)
    application.state.injected_runner = runner
    application.state.injected_answerer = answerer

    @application.middleware("http")
    async def runtime_configuration(request, call_next):
        with settings_scope(settings):
            return await call_next(request)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(research_router, prefix="/api")
    application.include_router(events_router)
    application.include_router(history_router)
    application.include_router(exports_router)
    application.include_router(settings_router)
    application.include_router(tasks_router)
    application.include_router(followup_router)

    @application.get("/health")
    async def health() -> dict[str, str]:
        manager = getattr(application.state, "task_manager", None)
        followup = getattr(application.state, "followup_manager", None)
        if (manager and manager.storage_failed) or (followup and followup.storage_failed):
            return JSONResponse({"status": "unavailable", "code": "STORAGE_UNAVAILABLE"}, status_code=503)
        return {
            "status": "ok",
            "api_version": settings.api_version,
            "runner_mode": settings.research_runner_mode,
            "demo_instance_id": settings.demo_instance_id,
        }

    install_error_handlers(application)

    def openapi_with_events():
        if application.openapi_schema is None:
            schema = get_openapi(title=application.title, version=application.version, routes=application.routes)
            _, event_models = models_json_schema([(ResearchEvent, "validation")], ref_template="#/components/schemas/{model}")
            schema.setdefault("components", {}).setdefault("schemas", {}).update(event_models["$defs"])
            stream = schema["paths"]["/api/v1/research/tasks/{task_id}/events"]["get"]
            stream["responses"]["200"]["content"] = {"text/event-stream": {"schema": {"type": "string"}}}
            stream["x-event-schema"] = {"$ref": "#/components/schemas/ResearchEvent"}
            application.openapi_schema = schema
        return application.openapi_schema

    application.openapi = openapi_with_events
    return application


app = create_app()
