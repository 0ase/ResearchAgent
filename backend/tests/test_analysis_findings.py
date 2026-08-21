from backend.services.structured_output import AnalysisFinding, validate_analysis_findings


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
