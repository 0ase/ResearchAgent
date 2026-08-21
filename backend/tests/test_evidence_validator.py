from backend.services.evidence_validator import validate_result_evidence


def _state(**overrides):
    state = {
        "papers": [{"paper_id": "paper-1", "title": "Paper"}],
        "paper_claims": [
            {"claim_id": "claim-1", "paper_id": "paper-1", "chunk_ids": ["chunk-1"]}
        ],
        "chunks": [
            {
                "chunk_id": "chunk-1",
                "paper_id": "paper-1",
                "content": "The exact source sentence.",
                "content_type": "pdf",
                "page_start": 2,
                "page_end": 3,
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
                "excerpt": "exact source sentence",
                "content_type": "pdf",
                "page_start": 2,
                "page_end": 3,
                "support_type": "direct",
            }
        ],
    }
    state.update(overrides)
    return state


def test_direct_excerpt_and_relations_are_verified() -> None:
    result = validate_result_evidence(_state())

    assert result.invalid_count == 0
    assert result.citations[0]["valid"] is True
    assert result.evidence[0]["verified"] is True
    assert result.evidence[0]["content_type"] == "pdf"


def test_invalid_excerpt_is_unverified_but_report_is_retained() -> None:
    result = validate_result_evidence(
        _state(evidence=[{**_state()["evidence"][0], "excerpt": "rewritten by model"}])
    )

    assert result.invalid_count == 1
    assert result.evidence[0]["verified"] is False
    assert result.evidence[0]["support_type"] == "unverified"
    assert result.citations[0]["valid"] is False
    assert result.warnings


def test_abstract_evidence_is_explicit_and_page_range_is_checked() -> None:
    result = validate_result_evidence(
        _state(
            chunks=[
                {
                    "chunk_id": "chunk-abstract",
                    "paper_id": "paper-1",
                    "content": "Abstract source text.",
                    "content_type": "abstract",
                    "page_start": None,
                    "page_end": None,
                }
            ],
            citations=[
                {
                    "citation_id": "citation-abstract",
                    "section_id": "section-1",
                    "paper_id": "paper-1",
                    "claim_ids": [],
                    "evidence_ids": ["evidence-abstract"],
                }
            ],
            evidence=[
                {
                    "evidence_id": "evidence-abstract",
                    "paper_id": "paper-1",
                    "chunk_id": "chunk-abstract",
                    "excerpt": "Abstract source text",
                    "content_type": "abstract",
                    "support_type": "direct",
                    "page_start": 1,
                    "page_end": 1,
                }
            ],
        )
    )

    assert result.evidence[0]["content_type"] == "abstract"
    assert result.evidence[0]["verified"] is False
    assert any("page" in warning.lower() for warning in result.warnings)
