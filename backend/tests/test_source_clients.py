import httpx
import pytest

from backend.sources import arxiv_client, crossref_client, pubmed_client
from backend.sources import semantic_scholar_client
from backend.sources.errors import SourceSearchError


class _ErrorResponse:
    status_code = 503
    text = "service unavailable"

    def raise_for_status(self) -> None:
        raise httpx.HTTPStatusError(
            "service unavailable",
            request=httpx.Request("GET", "https://example.test"),
            response=httpx.Response(503),
        )


class _ErrorClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, *_args, **_kwargs):
        return _ErrorResponse()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("module", "search"),
    [
        (arxiv_client, arxiv_client.search_arxiv),
        (semantic_scholar_client, semantic_scholar_client.search_semantic_scholar),
        (pubmed_client, pubmed_client.search_pubmed),
        (crossref_client, crossref_client.search_crossref),
    ],
)
async def test_provider_http_failure_is_distinguishable_from_no_results(
    monkeypatch,
    module,
    search,
) -> None:
    async def no_sleep(*_args, **_kwargs):
        return None

    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **_kwargs: _ErrorClient())
    monkeypatch.setattr(module.asyncio, "sleep", no_sleep)

    with pytest.raises(SourceSearchError) as exc_info:
        await search("retrieval augmented generation", max_results=2, timeout=1)

    error = exc_info.value
    assert error.source in {"arxiv", "semantic_scholar", "pubmed", "crossref"}
    assert error.code in {"SOURCE_HTTP_ERROR", "SOURCE_RATE_LIMITED"}
    assert error.public_message
    assert "api_key" not in str(error).lower()


def test_source_error_serializes_only_safe_fields() -> None:
    error = SourceSearchError("arxiv", "SOURCE_TIMEOUT", "arxiv request timed out")

    assert error.as_dict() == {
        "source": "arxiv",
        "error_code": "SOURCE_TIMEOUT",
        "message": "arxiv request timed out",
    }
