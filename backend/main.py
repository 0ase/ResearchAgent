from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.errors import install_error_handlers
from backend.api.routes_events import router as events_router
from backend.api.routes_exports import router as exports_router
from backend.api.routes_history import router as history_router
from backend.api.routes_research import router as research_router
from backend.api.routes_settings import router as settings_router
from backend.api.routes_tasks import router as tasks_router
from backend.config import PROJECT_ENV_PATH, settings
from backend.db.connection import open_database
from backend.db.migrate import migrate_database
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
    await migrate_database(settings)
    database_factory = lambda: open_database(settings)
    event_recorder = EventRecorder(EventRepository(database_factory))
    runner = None
    if settings.research_runner_mode == "demo":
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
    )
    application.state.task_manager = manager
    application.state.event_recorder = event_recorder
    application.state.deepseek_settings_service = DeepSeekSettingsService(
        settings,
        PROJECT_ENV_PATH,
    )
    await manager.recover_interrupted_tasks()
    try:
        yield
    finally:
        await manager.shutdown()


def create_app() -> FastAPI:
    application = FastAPI(
        title="多Agent学术研究助手",
        version=settings.api_version,
        lifespan=lifespan,
    )
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

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "api_version": settings.api_version,
            "runner_mode": settings.research_runner_mode,
            "demo_instance_id": settings.demo_instance_id,
        }

    install_error_handlers(application)
    return application


app = create_app()
