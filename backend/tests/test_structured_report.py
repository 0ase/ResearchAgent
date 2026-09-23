from backend.domain.reports import (
    CitationDraft,
    ReportDraft,
    build_structured_report,
    make_citation_token,
    next_draft_version,
    report_has_substantive_text,
)


def test_structured_report_has_stable_sections_and_citation_tokens() -> None:
    citations = [
        CitationDraft(
            citation_id="citation-1",
            paper_id="paper-1",
            claim_ids=["claim-1"],
            chunk_ids=["chunk-1"],
        )
    ]
    report = build_structured_report(
        "# Introduction\n\nSupported claim [[CITE:citation-1]].\n\n## Gaps\n\nOpen question.",
        citations=citations,
        claim_ids={"claim-1"},
        chunk_ids={"chunk-1"},
        version=2,
    )

    assert report.version == 2
    assert [section.heading for section in report.sections] == ["Introduction", "Gaps"]
    assert report.sections[0].section_id == "section-2-1"
    assert report.sections[0].citation_ids == ["citation-1"]
    assert make_citation_token("citation-1") == "[[CITE:citation-1]]"
    assert next_draft_version(report) == 3


def test_citation_with_unknown_claim_or_token_is_invalid() -> None:
    report = build_structured_report(
        "# Report\n\n[[CITE:known]] [[CITE:missing]]",
        citations=[
            CitationDraft(
                citation_id="known",
                paper_id="paper-1",
                claim_ids=["missing-claim"],
                chunk_ids=[],
            )
        ],
        claim_ids={"claim-1"},
        chunk_ids=set(),
    )

    assert {citation.citation_id for citation in report.citations} == {"known", "missing"}
    assert all(citation.valid is False for citation in report.citations)


def test_report_draft_accepts_provider_report_alias() -> None:
    draft = ReportDraft.model_validate({"report": "# Chinese report"})

    assert draft.markdown == "# Chinese report"


def test_report_content_check_rejects_citation_only_markdown() -> None:
    assert not report_has_substantive_text("[[CITE:citation-1]] [[CITE:citation-2]]")
    assert not report_has_substantive_text('{"report": ""}')
    assert report_has_substantive_text("# Report\n\nA concise finding.")
