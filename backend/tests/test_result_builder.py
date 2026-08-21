import pytest

from backend.domain.errors import ResearchPipelineError
from backend.services.result_builder import build_result, validate_result_ready


def test_langgraph_state_becomes_stable_result_snapshot() -> None:
    result = build_result(
        "task-1",
        {
            "research_plan": [{"sub_query": "attention"}],
            "raw_papers": [{"title": "Paper A"}],
            "paper_insights": [{"source": "paper-a", "answer": "summary"}],
            "analysis_report": {"agreements": ["a"]},
            "critique": {"score": 8, "approved": True},
            "final_answer": "# Review",
            "errors": ["one source unavailable"],
        },
    )

    assert result.task_id == "task-1"
    assert result.report_markdown == "# Review"
    assert result.research_plan == [{"sub_query": "attention"}]
    assert result.papers == [{"title": "Paper A"}]
    assert result.statistics["papers_count"] == 1
    assert result.partial is True
    assert result.capabilities.supports_replay is False


@pytest.mark.parametrize(
    ("state", "code"),
    [
        ({}, "NO_RESEARCH_RESULTS"),
        ({"raw_papers": [{"paper_id": "paper-1"}]}, "NO_READABLE_PAPERS"),
        (
            {
                "raw_papers": [{"paper_id": "paper-1"}],
                "paper_insights": [{"paper_id": "paper-1", "answer": "summary"}],
                "final_answer": "[[CITE:citation-1]] [[CITE:citation-2]]",
            },
            "EMPTY_REPORT",
        ),
    ],
)
def test_empty_result_states_have_stable_pipeline_errors(state: dict, code: str) -> None:
    result = build_result("task-1", state)

    with pytest.raises(ResearchPipelineError) as exc_info:
        validate_result_ready(result)

    assert exc_info.value.code == code


def test_non_empty_report_with_warnings_is_partial_but_ready() -> None:
    result = build_result(
        "task-1",
        {
            "raw_papers": [{"paper_id": "paper-1"}],
            "paper_insights": [{"paper_id": "paper-1", "answer": "summary"}],
            "final_answer": "# Report",
            "warnings": ["EMBEDDING_NOT_CONFIGURED"],
        },
    )

    validate_result_ready(result)
    assert result.partial is True
    assert result.warnings == ["EMBEDDING_NOT_CONFIGURED"]


def test_result_builder_materializes_citations_and_evidence_from_claims() -> None:
    result = build_result(
        "task-1",
        {
            "task_id": "task-1",
            "raw_papers": [{"paper_id": "paper-1", "title": "Paper 1"}],
            "paper_insights": [{"paper_id": "paper-1", "answer": "Summary"}],
            "paper_claims": [
                {
                    "claim_id": "claim-1",
                    "paper_id": "paper-1",
                    "statement": "A source claim",
                    "support_type": "direct",
                    "chunk_ids": ["chunk-1"],
                    "evidence_text": "A source claim",
                }
            ],
            "chunks": [
                {
                    "chunk_id": "chunk-1",
                    "paper_id": "paper-1",
                    "content": "A source claim from the paper.",
                    "content_type": "abstract",
                    "page_start": None,
                    "page_end": None,
                }
            ],
            "structured_report": {
                "sections": [{"section_id": "section-1", "citation_ids": ["citation-1"]}],
                "citations": [
                    {
                        "citation_id": "citation-1",
                        "claim_ids": ["claim-1"],
                        "chunk_ids": ["chunk-1"],
                    }
                ],
            },
            "final_answer": "# Report [[CITE:citation-1]]",
        },
    )

    assert result.citations[0]["valid"] is True
    assert result.evidence[0]["verified"] is True


def test_result_builder_links_chunk_only_citations_to_evidence() -> None:
    result = build_result(
        "task-1",
        {
            "task_id": "task-1",
            "raw_papers": [{"paper_id": "paper-1", "title": "Paper 1"}],
            "paper_insights": [{"paper_id": "paper-1", "answer": "Summary"}],
            "paper_claims": [
                {
                    "claim_id": "claim-1",
                    "paper_id": "paper-1",
                    "statement": "A source claim",
                    "support_type": "direct",
                    "chunk_ids": ["chunk-1"],
                    "evidence_text": "A source claim",
                }
            ],
            "chunks": [
                {
                    "chunk_id": "chunk-1",
                    "paper_id": "paper-1",
                    "content": "A source claim from the paper.",
                    "content_type": "abstract",
                }
            ],
            "structured_report": {
                "sections": [
                    {"section_id": "section-1", "citation_ids": ["citation-1"]}
                ],
                "citations": [
                    {
                        "citation_id": "citation-1",
                        "paper_id": "paper-1",
                        "claim_ids": [],
                        "chunk_ids": ["chunk-1"],
                    }
                ],
            },
            "final_answer": "# Report [[CITE:citation-1]]",
        },
    )

    assert result.citations[0]["evidence_ids"] == [result.evidence[0]["evidence_id"]]
