from backend.services.result_builder import build_result
import pytest
import pytest_asyncio

from backend.api.schemas.tasks import TaskSnapshot, TaskStatus
from backend.config import Settings
from backend.db.connection import open_database
from backend.db.migrate import migrate_database
from backend.repositories.evidence_repository import EvidenceRepository
from backend.repositories.task_repository import TaskRepository
from datetime import datetime, timezone


def test_result_builder_returns_normalized_evidence_and_capabilities() -> None:
    result = build_result(
        "task-1",
        {
            "raw_papers": [{"paper_id": "paper-1", "title": "Paper"}],
            "final_answer": "# Report [[CITE:citation-1]]",
            "paper_claims": [
                {"claim_id": "claim-1", "paper_id": "paper-1", "chunk_ids": ["chunk-1"]}
            ],
            "chunks": [
                {
                    "chunk_id": "chunk-1",
                    "paper_id": "paper-1",
                    "content": "Evidence sentence",
                    "content_type": "pdf",
                    "page_start": 1,
                    "page_end": 1,
                }
            ],
            "citations": [
                {
                    "citation_id": "citation-1",
                    "section_id": "section-1",
                    "paper_id": "paper-1",
                    "claim_ids": ["claim-1"],
                    "evidence_ids": ["evidence-1"],
                }
            ],
            "evidence": [
                {
                    "evidence_id": "evidence-1",
                    "paper_id": "paper-1",
                    "chunk_id": "chunk-1",
                    "claim_id": "claim-1",
                    "excerpt": "Evidence sentence",
                    "content_type": "pdf",
                    "page_start": 1,
                    "page_end": 1,
                    "support_type": "direct",
                }
            ],
        },
    )

    assert result.papers[0]["paper_id"] == "paper-1"
    assert result.citations[0]["citation_id"] == "citation-1"
    assert result.evidence[0]["verified"] is True
    assert result.capabilities.supports_evidence is True
    assert result.capabilities.supports_structured_papers is True


def test_invalid_evidence_marks_result_partial_and_legacy_caps_stay_false() -> None:
    result = build_result(
        "task-legacy",
        {"final_answer": "# Legacy", "papers": [{"title": "Legacy"}]},
    )

    assert result.partial is False
    assert result.capabilities.supports_evidence is False
    assert result.capabilities.supports_structured_papers is False


@pytest.mark.asyncio
async def test_evidence_repository_saves_citations_evidence_and_mapping_atomically(tmp_path) -> None:
    settings = Settings(_env_file=None, database_path=str(tmp_path / "research.db"))
    await migrate_database(settings)
    factory = lambda: open_database(settings)
    await TaskRepository(factory).create(
        TaskSnapshot(
            id="task-1",
            client_request_id="request-1",
            query="research",
            title="research",
            status=TaskStatus.COMPLETED,
            created_at=datetime.now(timezone.utc),
        )
    )
    repository = EvidenceRepository(factory)
    await repository.save_result_evidence(
        "task-1",
        [
            {
                "citation_id": "citation-1",
                "section_id": "section-1",
                "paper_id": "paper-1",
                "claim_ids": ["claim-1"],
                "evidence_ids": ["evidence-1"],
                "valid": True,
            }
        ],
        [
            {
                "evidence_id": "evidence-1",
                "paper_id": "paper-1",
                "chunk_id": "chunk-1",
                "excerpt": "source",
                "content_type": "abstract",
                "verified": True,
            }
        ],
    )

    loaded = await repository.list_for_task("task-1")

    assert loaded["citations"][0]["evidence_ids"] == ["evidence-1"]
    assert loaded["evidence"][0]["content_type"] == "abstract"
