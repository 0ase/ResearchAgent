from backend.services.structured_output import AnalysisFinding, validate_analysis_findings
from types import SimpleNamespace

import pytest

from backend.agents import analyze


@pytest.mark.asyncio
@pytest.mark.parametrize("output", ['{"findings": []}', 'not JSON'])
async def test_analysis_reentry_invalidates_previous_report_and_approval(monkeypatch, output):
    async def create(**kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=output))])

    monkeypatch.setattr(analyze, "AsyncOpenAI", lambda **kwargs: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    state = {
        "paper_insights": [{"paper_id": "p1", "answer": "Evidence", "claims": []}],
        "draft_sections": [{"content": "Old report"}], "approved": True,
        "critique": {"score": 9}, "structured_report": {"old": True},
        "citations": [{"citation_id": "old"}], "final_answer": "Old report",
        "critique_round": 1,
    }
    updated = {**state, **(await analyze.analyze_papers(state))}
    assert updated["analysis_report"] is not None
    assert updated["draft_sections"] == []
    assert updated["structured_report"] == {}
    assert updated["citations"] == []
    assert updated["approved"] is False
    assert updated["critique"] is None
    assert updated["final_answer"] is None
    assert updated["critique_round"] == 1


def test_agreement_requires_two_existing_claims() -> None:
    findings = validate_analysis_findings(
        [
            AnalysisFinding(
                finding_id="finding-1",
                kind="agreement",
                statement="Both papers report improved grounding.",
                claim_ids=["claim-1"],
                paper_ids=["paper-1"],
            ),
            AnalysisFinding(
                finding_id="finding-2",
                kind="agreement",
                statement="Both papers report improved grounding.",
                claim_ids=["claim-1", "claim-2"],
                paper_ids=["paper-1", "paper-2"],
            ),
        ],
        claim_ids={"claim-1", "claim-2"},
        paper_ids={"paper-1", "paper-2"},
    )

    assert findings[0].valid is False
    assert findings[1].valid is True


def test_gap_is_explicitly_an_analysis_inference_and_unknown_refs_are_invalid() -> None:
    findings = validate_analysis_findings(
        [
            AnalysisFinding(
                finding_id="gap-1",
                kind="gap",
                statement="Longitudinal evidence is limited.",
                claim_ids=[],
                paper_ids=["paper-1"],
            ),
            AnalysisFinding(
                finding_id="finding-2",
                kind="contradiction",
                statement="Unknown claim.",
                claim_ids=["missing-claim"],
                paper_ids=["paper-1"],
            ),
        ],
        claim_ids={"claim-1"},
        paper_ids={"paper-1"},
    )

    assert findings[0].support_type == "analysis_inference"
    assert findings[1].valid is False
    assert findings[1].claim_ids == []
