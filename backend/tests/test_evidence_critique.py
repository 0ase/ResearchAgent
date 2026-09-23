from backend.domain.reports import CitationDraft, build_structured_report, review_report


def test_critic_reports_uncited_claims_invalid_citations_and_overreliance() -> None:
    report = build_structured_report(
        "# Findings\n\n[[CITE:citation-1]] [[CITE:unknown]]",
        citations=[
            CitationDraft(
                citation_id="citation-1",
                paper_id="paper-1",
                claim_ids=["claim-1"],
                chunk_ids=["chunk-1"],
            )
        ],
        claim_ids={"claim-1", "claim-2"},
        chunk_ids={"chunk-1"},
    )

    critique = review_report(
        report,
        claim_ids={"claim-1", "claim-2"},
        paper_ids={"paper-1", "paper-2"},
    )

    assert "claim-2" in critique.evidence_review.uncited_claim_ids
    assert "unknown" in critique.evidence_review.invalid_citation_ids
    assert any(issue.code == "PAPER_OVERRELIANCE" for issue in critique.issues)
    assert critique.round == 1


def test_valid_report_can_be_approved_and_round_is_explicit() -> None:
    report = build_structured_report(
        "# Findings\n\n[[CITE:citation-1]] [[CITE:citation-2]]",
        citations=[
            CitationDraft(
                citation_id="citation-1",
                paper_id="paper-1",
                claim_ids=["claim-1"],
                chunk_ids=["chunk-1"],
            ),
            CitationDraft(
                citation_id="citation-2",
                paper_id="paper-2",
                claim_ids=["claim-2"],
                chunk_ids=["chunk-2"],
            ),
        ],
        claim_ids={"claim-1", "claim-2"},
        chunk_ids={"chunk-1", "chunk-2"},
    )

    critique = review_report(
        report,
        claim_ids={"claim-1", "claim-2"},
        paper_ids={"paper-1", "paper-2"},
        round_number=2,
    )

    assert critique.round == 2
    assert critique.approved is True
    assert critique.evidence_review.invalid_citation_ids == []
