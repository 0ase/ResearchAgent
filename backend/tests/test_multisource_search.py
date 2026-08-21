import pytest

import backend.agents.search as search_module
from backend.sources.errors import SourceSearchError


def _paper(title: str, source: str, index: int) -> dict:
    return {
        "title": title,
        "source": source,
        "source_id": f"{source}:{index}",
        "abstract": f"A real abstract for {title}.",
        "pdf_url": f"https://example.test/{source}-{index}.pdf",
        "published_date": "2024",
    }


@pytest.mark.asyncio
async def test_search_uses_retrieval_query_for_non_crossref_sources(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    async def fake_source(source: str, query: str, **_kwargs):
        calls.append((source, query))
        return [_paper(f"{source} paper", source, 1)]

    monkeypatch.setattr(
        search_module,
        "SOURCE_CLIENTS",
        {
            source: (lambda query, _source=source, **kwargs: fake_source(_source, query, **kwargs))
            for source in ["arxiv", "semantic_scholar", "pubmed", "crossref"]
        },
    )

    result = await search_module.search_papers(
        {
            "user_query": "RAG 的事实性",
            "research_plan": [
                {
                    "sub_query": "RAG 的事实性",
                    "display_query": "RAG 的事实性",
                    "retrieval_query": "retrieval augmented generation factuality",
                }
            ],
            "sources": ["arxiv", "semantic_scholar", "pubmed", "crossref"],
            "max_papers": 4,
            "search_round": 0,
        }
    )

    assert calls
    assert all(query == "retrieval augmented generation factuality" for _, query in calls)
    assert len(result["raw_papers"]) == 4


@pytest.mark.asyncio
async def test_search_balances_final_papers_across_available_sources(monkeypatch) -> None:
    async def arxiv(query, **_kwargs):
        return [_paper(f"arxiv-{index}", "arxiv", index) for index in range(5)]

    async def semantic_scholar(query, **_kwargs):
        return [_paper(f"s2-{index}", "semantic_scholar", index) for index in range(5)]

    async def no_results(query, **_kwargs):
        return []

    monkeypatch.setattr(
        search_module,
        "SOURCE_CLIENTS",
        {
            "arxiv": arxiv,
            "semantic_scholar": semantic_scholar,
            "pubmed": no_results,
            "crossref": no_results,
        },
    )

    result = await search_module.search_papers(
        {
            "user_query": "retrieval augmented generation",
            "research_plan": [{"sub_query": "retrieval augmented generation"}],
            "sources": ["arxiv", "semantic_scholar", "pubmed", "crossref"],
            "max_papers": 4,
            "search_round": 0,
        }
    )

    assert {paper["source"] for paper in result["raw_papers"]} == {
        "arxiv",
        "semantic_scholar",
    }
    assert len(result["raw_papers"]) == 4
    assert result["search_diagnostics"][0]["source"] in {
        "arxiv",
        "semantic_scholar",
        "pubmed",
        "crossref",
    }


@pytest.mark.asyncio
async def test_search_keeps_other_sources_when_one_source_fails(monkeypatch) -> None:
    async def failed_source(query, **_kwargs):
        raise SourceSearchError("arxiv", "SOURCE_TIMEOUT", "arxiv request timed out")

    async def available_source(query, **_kwargs):
        return [_paper("Available paper", "semantic_scholar", 1)]

    monkeypatch.setattr(
        search_module,
        "SOURCE_CLIENTS",
        {"arxiv": failed_source, "semantic_scholar": available_source},
    )

    result = await search_module.search_papers(
        {
            "user_query": "retrieval augmented generation",
            "research_plan": [{"sub_query": "retrieval augmented generation"}],
            "sources": ["arxiv", "semantic_scholar"],
            "max_papers": 2,
            "search_round": 0,
        }
    )

    assert len(result["raw_papers"]) == 1
    assert any("SOURCE_TIMEOUT" in warning for warning in result["warnings"])
