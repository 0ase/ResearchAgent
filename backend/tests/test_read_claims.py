from backend.services.structured_output import (
    PaperClaim,
    PaperInsight,
    parse_model_output,
    validate_claims,
)


def test_direct_claim_requires_existing_chunk_from_same_paper() -> None:
    claims = [
        PaperClaim(
            claim_id="claim-1",
            paper_id="paper-1",
            statement="The method improves recall.",
            support_type="direct",
            chunk_ids=["chunk-1"],
            evidence_text="improves recall",
        ),
        PaperClaim(
            claim_id="claim-2",
            paper_id="paper-1",
            statement="This claim points to another paper.",
            support_type="direct",
            chunk_ids=["chunk-other"],
            evidence_text="not present",
        ),
    ]

    validated = validate_claims(
        claims,
        {
            "chunk-1": {"paper_id": "paper-1", "content": "The method improves recall."},
            "chunk-other": {"paper_id": "paper-2", "content": "Other evidence."},
        },
    )

    assert validated[0].support_type == "direct"
    assert validated[1].support_type != "direct"


def test_direct_excerpt_must_be_locatable_in_chunk() -> None:
    claim = PaperClaim(
        claim_id="claim-1",
        paper_id="paper-1",
        statement="A claim",
        support_type="direct",
        chunk_ids=["chunk-1"],
        evidence_text="missing phrase",
    )

    validated = validate_claims(
        [claim],
        {"chunk-1": {"paper_id": "paper-1", "content": "Available source text."}},
    )

    assert validated[0].support_type == "unverified"


def test_json_fence_is_repaired_once_and_invalid_json_degrades_to_summary() -> None:
    parsed = parse_model_output(
        "```json\n{\"paper_id\": \"paper-1\", \"summary\": \"Useful\"}\n```",
        PaperInsight,
    )
    fallback = parse_model_output("not json at all", PaperInsight, fallback_paper_id="paper-1")
    repaired = parse_model_output(
        '{"paper_id": "paper-1", "summary": "Trailing comma",}',
        PaperInsight,
    )

    assert parsed is not None
    assert parsed.summary == "Useful"
    assert fallback is not None
    assert fallback.summary == "not json at all"
    assert fallback.claims == []
    assert repaired is not None
    assert repaired.summary == "Trailing comma"
