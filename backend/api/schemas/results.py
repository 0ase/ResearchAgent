from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ResultCapabilities(BaseModel):
    supports_replay: bool = False
    supports_evidence: bool = False
    supports_structured_papers: bool = False


class ResearchPaperResult(BaseModel):
    """Typed contract for the fields a structured paper result may expose."""

    paper_id: str = ""
    canonical_id: str | None = None
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    abstract: str | None = None
    source: str = ""
    source_id: str = ""
    doi: str | None = None
    year: int | None = None
    citation_count: int | None = None
    pdf_url: str | None = None
    landing_page_url: str | None = None
    relevance_score: float | None = None
    relevance_reason: str | None = None
    selected: bool = False
    full_text_status: str = "unavailable"
    aliases: list[dict[str, Any]] = Field(default_factory=list)


class PaperClaimResponse(BaseModel):
    claim_id: str = ""
    paper_id: str = ""
    statement: str = ""
    support_type: str = "unverified"
    chunk_ids: list[str] = Field(default_factory=list)
    evidence_text: str | None = None
    valid: bool = True


class AnalysisFindingResponse(BaseModel):
    finding_id: str = ""
    kind: str = "gap"
    statement: str = ""
    claim_ids: list[str] = Field(default_factory=list)
    paper_ids: list[str] = Field(default_factory=list)
    support_type: str = "unverified"
    valid: bool = True


class EvidenceResponse(BaseModel):
    evidence_id: str = ""
    task_id: str = ""
    paper_id: str = ""
    chunk_id: str = ""
    claim_id: str | None = None
    excerpt: str = ""
    content_type: str = "pdf"
    page_start: int | None = None
    page_end: int | None = None
    support_type: str = "unverified"
    verified: bool = False
    validation_message: str | None = None


class CitationResponse(BaseModel):
    citation_id: str = ""
    section_id: str = ""
    paper_id: str = ""
    claim_ids: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    display_number: int | None = None
    valid: bool = True
    support_type: str = "direct"
    validation_message: str | None = None


class ReportSectionResponse(BaseModel):
    section_id: str = ""
    heading: str = ""
    level: int = 1
    markdown: str = ""
    citation_ids: list[str] = Field(default_factory=list)


class StructuredReportResponse(BaseModel):
    version: int = 1
    markdown: str = ""
    sections: list[ReportSectionResponse] = Field(default_factory=list)
    citations: list[CitationResponse] = Field(default_factory=list)


class ResearchTaskResult(BaseModel):
    task_id: str
    report_markdown: str = ""
    research_plan: list[dict[str, Any]] = Field(default_factory=list)
    # Kept as dictionaries for backward compatibility with legacy results;
    # structured snapshots always include the internal ``paper_id`` key.
    papers: list[dict[str, Any]] = Field(default_factory=list)
    paper_insights: list[dict[str, Any]] = Field(default_factory=list)
    paper_claims: list[dict[str, Any]] = Field(default_factory=list)
    analysis_findings: list[dict[str, Any]] = Field(default_factory=list)
    structured_report: dict[str, Any] = Field(default_factory=dict)
    analysis: dict[str, Any] = Field(default_factory=dict)
    critique: dict[str, Any] = Field(default_factory=dict)
    statistics: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    partial: bool = False
    warnings: list[str] = Field(default_factory=list)
    capabilities: ResultCapabilities = Field(default_factory=ResultCapabilities)


class ResearchTaskResultResponse(BaseModel):
    """Strict public result contract with legacy values normalized at the edge."""

    task_id: str
    report_markdown: str = ""
    research_plan: list[dict[str, Any]] = Field(default_factory=list)
    papers: list[ResearchPaperResult] = Field(default_factory=list)
    paper_insights: list[dict[str, Any]] = Field(default_factory=list)
    paper_claims: list[PaperClaimResponse] = Field(default_factory=list)
    analysis_findings: list[AnalysisFindingResponse] = Field(default_factory=list)
    structured_report: StructuredReportResponse = Field(default_factory=StructuredReportResponse)
    analysis: dict[str, Any] = Field(default_factory=dict)
    critique: dict[str, Any] = Field(default_factory=dict)
    statistics: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceResponse] = Field(default_factory=list)
    citations: list[CitationResponse] = Field(default_factory=list)
    partial: bool = False
    warnings: list[str] = Field(default_factory=list)
    capabilities: ResultCapabilities = Field(default_factory=ResultCapabilities)

    @classmethod
    def from_legacy(cls, result: ResearchTaskResult) -> "ResearchTaskResultResponse":
        return cls.model_validate(result.model_dump(mode="json"))
