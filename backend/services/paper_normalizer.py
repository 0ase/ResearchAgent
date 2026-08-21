from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from collections.abc import Iterable
from typing import Any

from backend.domain.papers import PAPER_TEXT_STATUSES, PaperSnapshot, PaperSourceAlias


def normalize_doi(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    doi = value.strip().rstrip(".,;)")
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
    doi = doi.strip().lower()
    return doi or None


def normalize_arxiv_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    arxiv_id = value.strip()
    arxiv_id = re.sub(r"^https?://arxiv\.org/(?:abs|pdf)/", "", arxiv_id, flags=re.IGNORECASE)
    arxiv_id = arxiv_id.removesuffix(".pdf")
    arxiv_id = re.sub(r"v\d+$", "", arxiv_id, flags=re.IGNORECASE)
    return arxiv_id or None


def normalize_title(value: Any) -> str:
    title = unicodedata.normalize("NFKC", str(value or ""))
    return " ".join(title.casefold().split())


def title_canonical_id(title: str) -> str:
    digest = hashlib.sha256(normalize_title(title).encode("utf-8")).hexdigest()
    return f"title:{digest}"


def normalize_paper(raw: dict[str, Any], *, task_id: str = "unassigned") -> PaperSnapshot:
    """Normalize one provider record into a stable task-owned paper snapshot."""
    title = _text(raw.get("title")) or "Untitled paper"
    source = _source_name(raw)
    source_id = _text(raw.get("source_id")) or _fallback_source_id(raw, source)
    doi = normalize_doi(raw.get("doi"))
    arxiv_id = normalize_arxiv_id(raw.get("arxiv_id")) or _arxiv_id_from_source(source_id)
    canonical_id = _canonical_id(doi=doi, arxiv_id=arxiv_id, title=title)
    landing_page_url = _landing_page(raw, source, source_id, doi, arxiv_id)
    alias = PaperSourceAlias(
        source=source,
        source_id=source_id,
        landing_page_url=landing_page_url,
    )
    paper_id = _paper_uuid(task_id, canonical_id)

    citation_count = _optional_int(raw.get("citation_count"))
    # PubMed search results historically supplied a hard-coded 0 because the
    # provider does not return citation counts in this query. Preserve that
    # absence as null rather than presenting a fabricated count.
    if source.casefold() == "pubmed" and citation_count == 0:
        citation_count = None

    explicit_status = _optional_text(raw.get("full_text_status") or raw.get("pdf_status"))
    status = (
        explicit_status
        if explicit_status in PAPER_TEXT_STATUSES
        else paper_text_status(
            abstract=_optional_text(raw.get("abstract")),
            pdf_url=_optional_url(raw.get("pdf_url")),
        )
    )

    return PaperSnapshot(
        paper_id=paper_id,
        task_id=task_id,
        canonical_id=canonical_id,
        title=title,
        authors=_authors(raw.get("authors")),
        abstract=_optional_text(raw.get("abstract")),
        year=_year(raw.get("year"), raw.get("published_date")),
        citation_count=citation_count,
        pdf_url=_optional_url(raw.get("pdf_url")),
        landing_page_url=landing_page_url,
        doi=doi,
        source=source,
        source_id=source_id,
        selected=bool(raw.get("selected", raw.get("is_selected", False))),
        relevance_score=_optional_float(raw.get("relevance_score")),
        relevance_reason=_optional_text(raw.get("relevance_reason")),
        aliases=[alias],
        full_text_status=status,
    )


def normalize_papers(raw_papers: Iterable[dict[str, Any]], *, task_id: str) -> list[PaperSnapshot]:
    """Merge records from different providers while retaining every source alias."""
    groups: list[dict[str, Any]] = []
    key_to_group: dict[str, int] = {}

    for raw in raw_papers:
        paper = normalize_paper(raw, task_id=task_id)
        keys = _identity_keys(raw, paper)
        group_index = next((key_to_group[key] for key in keys if key in key_to_group), None)
        if group_index is None:
            group_index = len(groups)
            groups.append({"paper": paper, "keys": set()})
        group = groups[group_index]
        group["paper"] = _merge_paper(group["paper"], paper)
        group["keys"].update(keys)
        for key in keys:
            key_to_group[key] = group_index

    return [group["paper"] for group in groups]


def _merge_paper(left: PaperSnapshot, right: PaperSnapshot) -> PaperSnapshot:
    stronger = _canonical_strength(right.canonical_id) > _canonical_strength(left.canonical_id)
    primary = right if _paper_quality(right) > _paper_quality(left) else left
    combined_abstract = left.abstract or right.abstract
    combined_pdf_url = left.pdf_url or right.pdf_url
    aliases = list(left.aliases)
    known_aliases = {(alias.source, alias.source_id) for alias in aliases}
    for alias in right.aliases:
        if (alias.source, alias.source_id) not in known_aliases:
            aliases.append(alias)
            known_aliases.add((alias.source, alias.source_id))

    return left.model_copy(
        update={
            "paper_id": right.paper_id if stronger else left.paper_id,
            "canonical_id": right.canonical_id if stronger else left.canonical_id,
            "title": left.title if left.title != "Untitled paper" else right.title,
            "authors": left.authors or right.authors,
            "abstract": left.abstract or right.abstract,
            "year": left.year if left.year is not None else right.year,
            "citation_count": (
                left.citation_count if left.citation_count is not None else right.citation_count
            ),
            "pdf_url": left.pdf_url or right.pdf_url,
            "landing_page_url": left.landing_page_url or right.landing_page_url,
            "doi": left.doi or right.doi,
            "selected": left.selected or right.selected,
            "relevance_score": (
                left.relevance_score if left.relevance_score is not None else right.relevance_score
            ),
            "relevance_reason": left.relevance_reason or right.relevance_reason,
            "aliases": aliases,
            "source": (
                right.source
                if _paper_quality(right) > _paper_quality(left)
                else left.source
            ),
            "source_id": (
                right.source_id
                if _paper_quality(right) > _paper_quality(left)
                else left.source_id
            ),
            "full_text_status": paper_text_status(
                abstract=combined_abstract,
                pdf_url=combined_pdf_url,
                explicit_status=(
                    primary.full_text_status
                    if primary.full_text_status == "pdf_failed"
                    else None
                ),
            ),
        }
    )


def paper_text_status(
    *,
    abstract: str | None,
    pdf_url: str | None,
    explicit_status: str | None = None,
) -> str:
    if explicit_status in PAPER_TEXT_STATUSES:
        return explicit_status
    has_abstract = bool((abstract or "").strip())
    has_pdf = bool((pdf_url or "").strip())
    if has_pdf and has_abstract:
        return "full"
    if has_pdf:
        return "full_no_abstract"
    if has_abstract:
        return "abstract_only"
    return "unavailable"


def _paper_quality(paper: PaperSnapshot) -> tuple[int, int, int]:
    status_rank = {
        "full": 4,
        "abstract_only": 3,
        "full_no_abstract": 2,
        "pdf_failed": 1,
        "unavailable": 0,
    }
    return (
        status_rank.get(paper.full_text_status, 0),
        int(bool(paper.authors)),
        int(paper.year is not None),
    )


def _identity_keys(raw: dict[str, Any], paper: PaperSnapshot) -> list[str]:
    keys = [f"title:{normalize_title(paper.title)}"]
    if paper.canonical_id.startswith("doi:"):
        keys.insert(0, paper.canonical_id)
    elif paper.canonical_id.startswith("arxiv:"):
        keys.insert(0, paper.canonical_id)
    source_id = paper.source_id.casefold()
    if source_id:
        keys.append(f"source:{source_id}")
    return keys


def _canonical_id(*, doi: str | None, arxiv_id: str | None, title: str) -> str:
    if doi:
        return f"doi:{doi}"
    if arxiv_id:
        return f"arxiv:{arxiv_id.casefold()}"
    return title_canonical_id(title)


def _paper_uuid(task_id: str, canonical_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"research-agent:{task_id}:{canonical_id}"))


def _source_name(raw: dict[str, Any]) -> str:
    source = _text(raw.get("source"))
    if source:
        return source
    source_id = _text(raw.get("source_id"))
    return source_id.split(":", maxsplit=1)[0] if ":" in source_id else "unknown"


def _fallback_source_id(raw: dict[str, Any], source: str) -> str:
    doi = normalize_doi(raw.get("doi"))
    arxiv_id = normalize_arxiv_id(raw.get("arxiv_id"))
    suffix = doi or arxiv_id or normalize_title(raw.get("title")) or "unknown"
    return f"{source}:{suffix}"


def _arxiv_id_from_source(source_id: str) -> str | None:
    if source_id.casefold().startswith("arxiv:"):
        return normalize_arxiv_id(source_id.split(":", maxsplit=1)[1])
    return None


def _landing_page(
    raw: dict[str, Any],
    source: str,
    source_id: str,
    doi: str | None,
    arxiv_id: str | None,
) -> str | None:
    explicit = _optional_url(raw.get("landing_page_url")) or _optional_url(raw.get("url"))
    if explicit:
        return explicit
    if doi:
        return f"https://doi.org/{doi}"
    if arxiv_id:
        return f"https://arxiv.org/abs/{arxiv_id}"
    if source.casefold() == "pubmed" and ":" in source_id:
        return f"https://pubmed.ncbi.nlm.nih.gov/{source_id.split(':', 1)[1]}/"
    return None


def _authors(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _optional_text(value: Any) -> str | None:
    text = _text(value)
    return text or None


def _optional_url(value: Any) -> str | None:
    return _optional_text(value)


def _year(*values: Any) -> int | None:
    for value in values:
        if isinstance(value, int) and 1000 <= value <= 3000:
            return value
        match = re.search(r"\b(19|20)\d{2}\b", str(value or ""))
        if match:
            return int(match.group(0))
    return None


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _canonical_strength(canonical_id: str) -> int:
    if canonical_id.startswith("doi:"):
        return 3
    if canonical_id.startswith("arxiv:"):
        return 2
    return 1
