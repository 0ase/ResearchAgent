from datetime import datetime, timezone

import pytest
import pytest_asyncio

from backend.api.schemas.tasks import TaskSnapshot, TaskStatus
from backend.config import Settings
from backend.db.connection import open_database
from backend.db.migrate import migrate_database
from backend.repositories.paper_repository import PaperRepository
from backend.repositories.task_repository import TaskRepository
from backend.services.paper_normalizer import normalize_papers


@pytest_asyncio.fixture
async def paper_repository(tmp_path) -> PaperRepository:
    settings = Settings(_env_file=None, database_path=str(tmp_path / "research.db"))
    await migrate_database(settings)
    factory = lambda: open_database(settings)
    tasks = TaskRepository(factory)
    await tasks.create(
        TaskSnapshot(
            id="task-1",
            client_request_id="request-1",
            query="research",
            title="research",
            status=TaskStatus.RUNNING,
            created_at=datetime.now(timezone.utc),
        )
    )
    return PaperRepository(factory)


@pytest.mark.asyncio
async def test_upsert_creates_one_main_record_and_source_aliases(paper_repository) -> None:
    papers = normalize_papers(
        [
            {
                "title": "Shared paper",
                "source": "arxiv",
                "source_id": "arxiv:1",
                "doi": "10.1234/shared",
            },
            {
                "title": "Shared paper",
                "source": "crossref",
                "source_id": "crossref:10.1234/shared",
                "doi": "10.1234/shared",
            },
        ],
        task_id="task-1",
    )

    saved = await paper_repository.upsert_task_papers("task-1", papers)
    loaded = await paper_repository.list_for_task("task-1")

    assert len(saved) == len(loaded) == 1
    assert loaded[0].paper_id == papers[0].paper_id
    assert {alias.source for alias in loaded[0].aliases} == {"arxiv", "crossref"}


@pytest.mark.asyncio
async def test_filter_selection_and_relevance_are_written_to_snapshot(paper_repository) -> None:
    paper = normalize_papers(
        [{"title": "Paper", "source": "arxiv", "source_id": "arxiv:1"}],
        task_id="task-1",
    )[0]
    await paper_repository.upsert_task_papers("task-1", [paper])

    updated = await paper_repository.update_selection(
        "task-1",
        paper.paper_id,
        selected=True,
        relevance_score=4.5,
        relevance_reason="Matches the question",
    )

    assert updated is not None
    assert updated.selected is True
    assert updated.relevance_score == 4.5
    assert updated.relevance_reason == "Matches the question"


@pytest.mark.asyncio
async def test_text_status_is_persisted_in_snapshot(paper_repository) -> None:
    paper = normalize_papers(
        [
            {
                "title": "Readable paper",
                "source": "semantic_scholar",
                "source_id": "semantic_scholar:1",
                "abstract": "A useful abstract.",
                "pdf_url": "https://example.test/paper.pdf",
            }
        ],
        task_id="task-1",
    )[0]

    await paper_repository.upsert_task_papers("task-1", [paper])
    loaded = (await paper_repository.list_for_task("task-1"))[0]

    assert loaded.full_text_status == "full"


@pytest.mark.asyncio
async def test_completed_task_metadata_is_not_overwritten(paper_repository) -> None:
    original = normalize_papers(
        [
            {
                "title": "Original title",
                "source": "crossref",
                "source_id": "crossref:10.1234/paper",
                "doi": "10.1234/paper",
                "year": 2020,
                "citation_count": 12,
                "pdf_url": "https://example.com/original.pdf",
            }
        ],
        task_id="task-1",
    )[0]
    await paper_repository.upsert_task_papers("task-1", [original])
    await paper_repository.lock_task_snapshot("task-1")

    changed = original.model_copy(
        update={
            "title": "Later provider title",
            "year": 2025,
            "citation_count": 999,
            "pdf_url": "https://example.com/later.pdf",
        }
    )
    await paper_repository.upsert_task_papers("task-1", [changed])
    loaded = (await paper_repository.list_for_task("task-1"))[0]

    assert loaded.title == "Original title"
    assert loaded.year == 2020
    assert loaded.citation_count == 12
    assert loaded.pdf_url == "https://example.com/original.pdf"
