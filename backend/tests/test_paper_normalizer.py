from uuid import UUID

from backend.services.paper_normalizer import (
    normalize_paper,
    normalize_papers,
    paper_text_status,
)


def test_doi_is_the_preferred_canonical_identity() -> None:
    paper = normalize_paper(
        {
            "title": "A useful paper",
            "source": "crossref",
            "source_id": "crossref:10.1234/ABC.1",
            "doi": "https://doi.org/10.1234/ABC.1.",
        },
        task_id="task-1",
    )

    assert paper.canonical_id == "doi:10.1234/abc.1"
    assert UUID(paper.paper_id).version == 5
    assert paper.doi == "10.1234/abc.1"
    assert paper.landing_page_url == "https://doi.org/10.1234/abc.1"


def test_arxiv_then_title_hash_are_fallback_identities() -> None:
    arxiv = normalize_paper(
        {
            "title": "A paper",
            "source": "arxiv",
            "source_id": "arxiv:2301.01234v2",
        },
        task_id="task-1",
    )
    title_only = normalize_paper(
        {"title": "  A   PAPER  ", "source": "pubmed", "source_id": "pubmed:9"},
        task_id="task-1",
    )

    assert arxiv.canonical_id == "arxiv:2301.01234"
    assert title_only.canonical_id.startswith("title:")
    assert len(title_only.canonical_id.removeprefix("title:")) == 64


def test_multi_source_records_merge_into_one_paper_with_aliases() -> None:
    papers = normalize_papers(
        [
            {
                "title": "A Shared Discovery",
                "source": "arxiv",
                "source_id": "arxiv:2401.00001",
                "abstract": "An abstract",
            },
            {
                "title": "A shared discovery",
                "source": "semantic_scholar",
                "source_id": "semantic_scholar:S2-1",
                "doi": "10.5555/shared",
                "year": 2024,
            },
        ],
        task_id="task-1",
    )

    assert len(papers) == 1
    assert papers[0].canonical_id == "doi:10.5555/shared"
    assert {alias.source for alias in papers[0].aliases} == {"arxiv", "semantic_scholar"}
    assert {alias.source_id for alias in papers[0].aliases} == {
        "arxiv:2401.00001",
        "semantic_scholar:S2-1",
    }


def test_missing_metadata_is_null_instead_of_zero_or_empty_url() -> None:
    paper = normalize_paper(
        {"title": "Incomplete metadata", "source": "pubmed", "source_id": "pubmed:1"},
        task_id="task-1",
    )

    assert paper.year is None
    assert paper.citation_count is None
    assert paper.pdf_url is None


def test_metadata_merge_prefers_source_with_abstract_and_pdf() -> None:
    papers = normalize_papers(
        [
            {
                "title": "Shared paper",
                "source": "crossref",
                "source_id": "crossref:10.1234/shared",
                "doi": "10.1234/shared",
            },
            {
                "title": "Shared paper",
                "source": "semantic_scholar",
                "source_id": "semantic_scholar:S2-1",
                "doi": "10.1234/shared",
                "abstract": "A real abstract from a secondary source.",
                "pdf_url": "https://example.test/paper.pdf",
            },
        ],
        task_id="task-1",
    )

    assert len(papers) == 1
    assert papers[0].source == "semantic_scholar"
    assert papers[0].abstract == "A real abstract from a secondary source."
    assert papers[0].pdf_url == "https://example.test/paper.pdf"
    assert papers[0].full_text_status == "full"
    assert {alias.source for alias in papers[0].aliases} == {
        "crossref",
        "semantic_scholar",
    }


def test_metadata_merge_derives_status_from_combined_sources() -> None:
    papers = normalize_papers(
        [
            {
                "title": "Combined metadata",
                "source": "crossref",
                "source_id": "crossref:10.1234/combined",
                "doi": "10.1234/combined",
                "pdf_url": "https://example.test/combined.pdf",
            },
            {
                "title": "Combined metadata",
                "source": "semantic_scholar",
                "source_id": "semantic_scholar:S2-combined",
                "doi": "10.1234/combined",
                "abstract": "Abstract recovered from another source.",
            },
        ],
        task_id="task-1",
    )

    assert papers[0].full_text_status == "full"
    assert papers[0].source == "semantic_scholar"


def test_paper_text_status_distinguishes_missing_abstract() -> None:
    assert paper_text_status(abstract="Abstract", pdf_url="paper.pdf") == "full"
    assert paper_text_status(abstract="Abstract", pdf_url=None) == "abstract_only"
    assert paper_text_status(abstract=None, pdf_url="paper.pdf") == "full_no_abstract"
    assert paper_text_status(abstract=None, pdf_url=None) == "unavailable"
