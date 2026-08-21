from __future__ import annotations

from typing import Any

from backend.api.schemas.results import ResearchTaskResult
from backend.domain.errors import ResearchPipelineError
from backend.domain.reports import citation_id_for_claim, report_has_substantive_text
from backend.services.evidence_validator import validate_result_evidence


def build_result(
    task_id: str,
    state: dict[str, Any] | None,
    *,
    supports_replay: bool = False,
) -> ResearchTaskResult:
    state = state or {}
    papers = [_result_paper(paper) for paper in (state.get("raw_papers", []) or [])]
    errors = [str(error) for error in (state.get("errors", []) or [])]
    state_warnings = [str(warning) for warning in (state.get("warnings", []) or [])]
    critique = state.get("critique") or {}
    paper_claims = state.get("paper_claims", []) or []
    analysis_findings = state.get("analysis_findings", []) or []
    evidence_state = {**state, "papers": papers}
    if not evidence_state.get("evidence") or not evidence_state.get("citations"):
        derived_evidence, derived_citations = _derive_evidence_and_citations(state)
        evidence_state.setdefault("evidence", derived_evidence)
        evidence_state.setdefault("citations", derived_citations)
        if not evidence_state.get("evidence"):
            evidence_state["evidence"] = derived_evidence
        if not evidence_state.get("citations"):
            evidence_state["citations"] = derived_citations
    evidence_result = validate_result_evidence(evidence_state)
    warnings = _unique_preserving_order(errors + state_warnings + evidence_result.warnings)
    statistics = {
        "papers_count": len(papers),
        "selected_papers_count": len(state.get("selected_papers", []) or []),
        "paper_insights_count": len(state.get("paper_insights", []) or []),
        "papers_read": len(state.get("paper_insights", []) or []),
        "critique_score": critique.get("score"),
        "critique_round": state.get("critique_round", 0),
        "paper_claims_count": len(paper_claims),
        "analysis_findings_count": len(analysis_findings),
    }
    return ResearchTaskResult(
        task_id=task_id,
        report_markdown=state.get("final_answer") or "",
        research_plan=state.get("research_plan", []) or [],
        papers=papers,
        paper_insights=state.get("paper_insights", []) or [],
        paper_claims=paper_claims,
        analysis_findings=analysis_findings,
        structured_report=state.get("structured_report", {}) or {},
        analysis=state.get("analysis_report") or {},
        critique=critique,
        statistics=statistics,
        evidence=evidence_result.evidence,
        citations=evidence_result.citations,
        partial=bool(warnings),
        warnings=warnings,
        capabilities={
            "supports_replay": supports_replay,
            "supports_evidence": bool(evidence_result.evidence or evidence_result.citations),
            "supports_structured_papers": bool(
                papers and all(paper.get("paper_id") for paper in papers)
            ),
        },
    )


def validate_result_ready(result: ResearchTaskResult) -> None:
    """Reject a state that cannot produce a meaningful research result."""
    if not result.papers:
        raise ResearchPipelineError("NO_RESEARCH_RESULTS")
    if not result.paper_insights:
        raise ResearchPipelineError("NO_READABLE_PAPERS")
    if not report_has_substantive_text(result.report_markdown):
        raise ResearchPipelineError("EMPTY_REPORT")


def _unique_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def _derive_evidence_and_citations(state: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """Materialize API evidence from validated claims and durable chunks.

    The graph stores the structured report and claims as its canonical state;
    this adapter supplies the richer REST shape without requiring every agent
    to duplicate evidence bookkeeping.
    """
    claims = [claim for claim in (state.get("paper_claims") or []) if claim.get("claim_id")]
    chunks = {
        chunk.get("chunk_id"): chunk
        for chunk in (state.get("chunks") or [])
        if chunk.get("chunk_id")
    }
    evidence: list[dict] = []
    evidence_by_claim_chunk: dict[tuple[str, str], str] = {}
    evidence_by_chunk: dict[str, list[str]] = {}
    for claim in claims:
        claim_id = str(claim["claim_id"])
        for chunk_id in claim.get("chunk_ids", []) or []:
            chunk = chunks.get(chunk_id)
            if chunk is None:
                continue
            evidence_id = f"evidence:{claim_id}:{chunk_id}"
            excerpt = str(claim.get("evidence_text") or chunk.get("content") or "").strip()
            if not excerpt or excerpt not in str(chunk.get("content") or ""):
                excerpt = str(chunk.get("content") or "")[:500]
            item = {
                "evidence_id": evidence_id,
                "task_id": state.get("task_id", ""),
                "paper_id": claim.get("paper_id") or chunk.get("paper_id", ""),
                "chunk_id": chunk_id,
                "claim_id": claim_id,
                "excerpt": excerpt,
                "content_type": chunk.get("content_type", "pdf"),
                "page_start": chunk.get("page_start"),
                "page_end": chunk.get("page_end"),
                "support_type": claim.get("support_type", "unverified"),
            }
            evidence.append(item)
            evidence_by_claim_chunk[(claim_id, chunk_id)] = evidence_id
            evidence_by_chunk.setdefault(str(chunk_id), []).append(evidence_id)

    structured = state.get("structured_report") or {}
    sections = structured.get("sections", []) if isinstance(structured, dict) else []
    raw_citations = structured.get("citations", []) if isinstance(structured, dict) else []
    citations: list[dict] = []
    for index, raw in enumerate(raw_citations or [], start=1):
        citation = dict(raw)
        citation_id = str(citation.get("citation_id") or "")
        if not citation_id:
            continue
        claim_ids = [str(value) for value in citation.get("claim_ids", []) or []]
        chunk_ids = [str(value) for value in citation.get("chunk_ids", []) or []]
        claim_map = {str(claim["claim_id"]): claim for claim in claims}
        paper_id = citation.get("paper_id") or next(
            (claim_map[claim_id].get("paper_id") for claim_id in claim_ids if claim_id in claim_map),
            "",
        )
        evidence_ids = [
            evidence_by_claim_chunk[(claim_id, chunk_id)]
            for claim_id in claim_ids
            for chunk_id in chunk_ids or claim_map.get(claim_id, {}).get("chunk_ids", [])
            if (claim_id, chunk_id) in evidence_by_claim_chunk
        ]
        if not evidence_ids:
            evidence_ids = [
                evidence_id
                for chunk_id in chunk_ids
                for evidence_id in evidence_by_chunk.get(chunk_id, [])
            ]
        section_id = next(
            (
                str(section.get("section_id"))
                for section in sections
                if citation_id in (section.get("citation_ids") or [])
            ),
            str(sections[0].get("section_id")) if sections else "section-1-1",
        )
        citations.append(
            {
                "citation_id": citation_id,
                "section_id": section_id,
                "paper_id": paper_id,
                "claim_ids": claim_ids,
                "chunk_ids": chunk_ids,
                "evidence_ids": list(dict.fromkeys(evidence_ids)),
                "display_number": citation.get("display_number") or index,
            }
        )

    if not citations:
        # A provider may return a valid report without echoing the citation
        # catalogue. Expose deterministic claim citations rather than dropping
        # all evidence from the public result.
        for index, claim in enumerate(claims, start=1):
            claim_id = str(claim["claim_id"])
            claim_chunks = [str(value) for value in claim.get("chunk_ids", []) or []]
            citations.append(
                {
                    "citation_id": citation_id_for_claim(claim_id),
                    "section_id": str(sections[0].get("section_id")) if sections else "section-1-1",
                    "paper_id": claim.get("paper_id", ""),
                    "claim_ids": [claim_id],
                    "chunk_ids": claim_chunks,
                    "evidence_ids": [
                        evidence_by_claim_chunk[(claim_id, chunk_id)]
                        for chunk_id in claim_chunks
                        if (claim_id, chunk_id) in evidence_by_claim_chunk
                    ],
                    "display_number": index,
                }
            )
    return evidence, citations


def _result_paper(paper: Any) -> dict[str, Any]:
    result = dict(paper)
    if "paper_id" not in result and result.get("id"):
        result["paper_id"] = result["id"]
    return result
