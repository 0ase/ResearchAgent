from __future__ import annotations

from pydantic import BaseModel, Field


PAPER_TEXT_STATUSES = {
    "full",
    "abstract_only",
    "full_no_abstract",
    "unavailable",
    "pdf_failed",
}


class PaperSourceAlias(BaseModel):
    source: str
    source_id: str
    landing_page_url: str | None = None


class PaperSnapshot(BaseModel):
    """The task-owned, provider-neutral representation of a paper."""

    paper_id: str
    task_id: str
    canonical_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str | None = None
    year: int | None = None
    citation_count: int | None = None
    pdf_url: str | None = None
    landing_page_url: str | None = None
    doi: str | None = None
    source: str
    source_id: str
    selected: bool = False
    relevance_score: float | None = None
    relevance_reason: str | None = None
    aliases: list[PaperSourceAlias] = Field(default_factory=list)
    metadata_locked: bool = False
    full_text_status: str = "unavailable"

    def to_result_dict(self) -> dict:
        """Serialize the snapshot for API results without inventing metadata."""
        return {
            "id": self.paper_id,
            "paper_id": self.paper_id,
            "task_id": self.task_id,
            "canonical_id": self.canonical_id,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "year": self.year,
            "published_date": self.year,
            "citation_count": self.citation_count,
            "pdf_url": self.pdf_url,
            "landing_page_url": self.landing_page_url,
            "doi": self.doi,
            "source": self.source,
            "source_id": self.source_id,
            "selected": self.selected,
            "relevance_score": self.relevance_score,
            "relevance_reason": self.relevance_reason,
            "aliases": [alias.model_dump(mode="json") for alias in self.aliases],
            "full_text_status": self.full_text_status,
        }
