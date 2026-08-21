from __future__ import annotations

import re
import uuid
import json
from collections import Counter
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field


class CitationDraft(BaseModel):
    citation_id: str
    paper_id: str = ""
    claim_ids: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)
    display_number: int | None = None
    valid: bool = True


class ReportSection(BaseModel):
    section_id: str
    heading: str
    level: int
    markdown: str
    citation_ids: list[str] = Field(default_factory=list)


class StructuredReport(BaseModel):
    version: int = 1
    markdown: str = ""
    sections: list[ReportSection] = Field(default_factory=list)
    citations: list[CitationDraft] = Field(default_factory=list)


class ReportDraft(BaseModel):
    markdown: str = Field(
        validation_alias=AliasChoices("markdown", "report", "content", "text")
    )
    citations: list[CitationDraft] = Field(default_factory=list)


class CritiqueIssue(BaseModel):
    code: str
    message: str
    severity: Literal["warning", "error"] = "warning"


class EvidenceReview(BaseModel):
    uncited_claim_ids: list[str] = Field(default_factory=list)
    invalid_citation_ids: list[str] = Field(default_factory=list)
    cited_paper_ids: list[str] = Field(default_factory=list)


class CritiqueResult(BaseModel):
    round: int = 1
    score: float
    approved: bool
    issues: list[CritiqueIssue] = Field(default_factory=list)
    evidence_review: EvidenceReview = Field(default_factory=EvidenceReview)
    feedback: str = ""


def make_citation_token(citation_id: str) -> str:
    return f"[[CITE:{citation_id}]]"


def report_has_substantive_text(markdown: str) -> bool:
    """Return whether a draft contains readable prose beyond citation tokens.

    Citation markers are rendered as interactive controls in the UI.  They
    therefore cannot be the only content that makes a report appear non-empty.
    Provider responses may also arrive as a JSON object with an empty
    ``report``/``markdown`` field, so unwrap those aliases before checking.
    """
    candidate = str(markdown or "").strip()
    if not candidate:
        return False
    try:
        decoded = json.loads(candidate)
    except (TypeError, ValueError, json.JSONDecodeError):
        decoded = None
    if isinstance(decoded, dict):
        for key in ("markdown", "report", "content", "text"):
            if key in decoded:
                candidate = str(decoded.get(key) or "").strip()
                break
    candidate = re.sub(r"\[\[CITE:[^\]]+\]\]", "", candidate)
    candidate = re.sub(r"[\s#*_`~>|\-:;,./\\\[\]{}()\"']+", "", candidate)
    return len(candidate) >= 5


def citation_id_for_claim(claim_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"research-agent:citation:{claim_id}"))


def build_structured_report(
    markdown: str,
    *,
    citations: list[CitationDraft],
    claim_ids: set[str],
    chunk_ids: set[str],
    version: int = 1,
) -> StructuredReport:
    citation_map = {citation.citation_id: citation for citation in citations}
    token_ids = _citation_ids(markdown)
    normalized_citations: list[CitationDraft] = []
    for citation_id in token_ids:
        citation = citation_map.get(citation_id)
        if citation is None:
            normalized_citations.append(
                CitationDraft(citation_id=citation_id, valid=False)
            )
            continue
        valid = (
            bool(citation.claim_ids or citation.chunk_ids)
            and set(citation.claim_ids) <= claim_ids
            and set(citation.chunk_ids) <= chunk_ids
        )
        normalized_citations.append(citation.model_copy(update={"valid": valid}))

    sections = _sections(markdown, version, token_ids)
    return StructuredReport(
        version=version,
        markdown=markdown,
        sections=sections,
        citations=normalized_citations,
    )


def review_report(
    report: StructuredReport,
    *,
    claim_ids: set[str],
    paper_ids: set[str],
    round_number: int = 1,
) -> CritiqueResult:
    citations = list(report.citations)
    invalid_ids = [citation.citation_id for citation in citations if not citation.valid]
    cited_claim_ids = {
        claim_id
        for citation in citations
        if citation.valid
        for claim_id in citation.claim_ids
    }
    uncited_claim_ids = sorted(claim_ids - cited_claim_ids)
    cited_paper_ids = [citation.paper_id for citation in citations if citation.valid and citation.paper_id]
    issues: list[CritiqueIssue] = []
    if uncited_claim_ids:
        issues.append(
            CritiqueIssue(
                code="UNCITED_CLAIMS",
                message=f"Claims without a valid report citation: {', '.join(uncited_claim_ids)}",
            )
        )
    if invalid_ids:
        issues.append(
            CritiqueIssue(
                code="INVALID_CITATIONS",
                message=f"Invalid citation tokens: {', '.join(invalid_ids)}",
                severity="error",
            )
        )
    counts = Counter(cited_paper_ids)
    total = sum(counts.values())
    if len(paper_ids) > 1 and total and max(counts.values()) / total >= 0.75:
        issues.append(
            CritiqueIssue(
                code="PAPER_OVERRELIANCE",
                message="The draft relies too heavily on one paper.",
            )
        )

    score = max(0.0, 10.0 - (2.0 * len(issues)))
    evidence_review = EvidenceReview(
        uncited_claim_ids=uncited_claim_ids,
        invalid_citation_ids=invalid_ids,
        cited_paper_ids=sorted(set(cited_paper_ids)),
    )
    return CritiqueResult(
        round=round_number,
        score=score,
        approved=not issues,
        issues=issues,
        evidence_review=evidence_review,
        feedback="; ".join(issue.message for issue in issues),
    )


def next_draft_version(report: StructuredReport | dict | None) -> int:
    if report is None:
        return 1
    version = report.version if isinstance(report, StructuredReport) else int(report.get("version", 0))
    return version + 1


def _citation_ids(markdown: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\[\[CITE:([^\]]+)\]\]", markdown)))


def _sections(markdown: str, version: int, citation_ids: list[str]) -> list[ReportSection]:
    matches = list(re.finditer(r"(?m)^(#{1,6})\s+(.+?)\s*$", markdown))
    if not matches:
        return [
            ReportSection(
                section_id=f"section-{version}-1",
                heading="Report",
                level=1,
                markdown=markdown,
                citation_ids=citation_ids,
            )
        ]
    sections: list[ReportSection] = []
    for index, match in enumerate(matches, start=1):
        end = matches[index].start() if index < len(matches) else len(markdown)
        section_markdown = markdown[match.start() : end].strip()
        sections.append(
            ReportSection(
                section_id=f"section-{version}-{index}",
                heading=match.group(2).strip(),
                level=len(match.group(1)),
                markdown=section_markdown,
                citation_ids=_citation_ids(section_markdown),
            )
        )
    return sections
