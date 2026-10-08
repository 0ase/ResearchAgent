from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI

from backend.config import settings
from backend.core.errors import register_error_handlers
from backend.core.middleware import RequestTraceMiddleware
from backend.core.observability import configure_logging, logger, report_exception


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings)
    logger.info("application.started")
    try:
        yield
    except Exception as exc:
        report_exception(exc, "application.failed")
        raise
    finally:
        from backend.rag.vector_runtime import close_vector_store
        await asyncio.to_thread(close_vector_store)
        logger.info("application.stopped")


def create_app() -> FastAPI:
    from backend.api.routes_research import router as research_router

    application = FastAPI(title="多Agent学术研究助手", lifespan=lifespan)
    register_error_handlers(application)
    application.add_middleware(RequestTraceMiddleware)
    application.include_router(research_router, prefix="/api")

    @application.get("/health")
    async def health():
        return {"status": "ok"}

    return application


app = create_app()
