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


import json
from pathlib import Path
import pytest


@pytest.mark.parametrize("statement_key,evidence_key", [("claim", "evidence"), ("text", "excerpt"), ("statement", "evidence_text")])
def test_real_provider_shape_preserves_claims_and_canonical_identity(statement_key, evidence_key):
    from backend.services.structured_output import parse_paper_insight_output
    data = json.loads((Path(__file__).parent / "fixtures/read_provider_shape.json").read_text())
    for claim in data["claims"]:
        claim[statement_key] = claim.pop("claim")
        claim[evidence_key] = claim.pop("evidence_text")
        claim["paper_id"] = "wrong-title"
    data["limitations"] = "Missing independent baselines."
    insight, degraded = parse_paper_insight_output(json.dumps(data), canonical_paper_id="paper-1")
    assert not degraded
    assert insight.paper_id == "paper-1"
    assert insight.limitations == ["Missing independent baselines."]
    assert len(insight.claims) == 2
    for n, claim in enumerate(insight.claims, 1):
        assert claim.paper_id == "paper-1"
        assert claim.claim_id == f"paper-1:claim:{n}"
        assert claim.chunk_ids == [f"chunk-{n}"]
    assert all(c.support_type == "direct" for c in validate_claims(insight.claims, {
        f"chunk-{n}": {"paper_id": "paper-1", "content": f"Source evidence {n}."} for n in (1, 2)
    }))


@pytest.mark.parametrize("text,summary", [
    ('{"summary":"Safe summary", "claims":[{"bad":1}], "limitations":{}}', "Safe summary"),
    ('{"answer":"Safe answer", "claims":{}}', "Safe answer"),
    ('{"unknown":1}', ""), ('{"summary":"truncated', ""), ('[broken', ""),
    ('plain text summary', 'plain text summary'),
])
def test_invalid_structured_output_never_becomes_json_summary(text, summary):
    from backend.services.structured_output import parse_paper_insight_output
    insight, degraded = parse_paper_insight_output(text, canonical_paper_id="paper-1")
    assert degraded
    assert insight.summary == summary
    assert insight.paper_id == "paper-1"


@pytest.mark.parametrize("broken_field", ["claims", "limitations"])
def test_partial_invalid_structure_keeps_valid_claims_and_reports_loss(broken_field):
    from backend.services.structured_output import parse_paper_insight_output
    data = json.loads((Path(__file__).parent / "fixtures/read_provider_shape.json").read_text())
    data[broken_field].append({"invalid": "object"})
    insight, degraded = parse_paper_insight_output(json.dumps(data), canonical_paper_id="paper-1")
    assert degraded
    assert len(insight.claims) == 2
    assert insight.limitations == ["Missing independent baselines."]
