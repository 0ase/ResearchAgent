from types import SimpleNamespace

import pytest

import backend.agents.filter as filter_module


def test_parse_scores_accepts_objects_arrays_and_code_blocks() -> None:
    assert filter_module._parse_scores('{"scores":[{"paper_num":1,"score":4}]}')[0][
        "score"
    ] == 4
    assert filter_module._parse_scores('[{"paper_num":2,"score":3}]')[0][
        "paper_num"
    ] == 2
    assert filter_module._parse_scores('```json\n{"scores": []}\n```') == []


def test_deterministic_score_uses_english_retrieval_terms() -> None:
    score, reason = filter_module._deterministic_score(
        {
            "title": "Retrieval augmented generation for factual question answering",
            "abstract": "A study of retrieval grounding.",
            "pdf_url": "https://example.test/paper.pdf",
        },
        query="知识密集型问答",
        retrieval_queries=["retrieval augmented generation factuality question answering"],
    )

    assert score >= 4
    assert "retrieval" in reason.lower()


@pytest.mark.asyncio
async def test_invalid_model_scores_use_deterministic_readable_fallback(monkeypatch) -> None:
    class FakeCompletions:
        async def create(self, **_kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))]
            )

    class FakeClient:
        def __init__(self, **_kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(filter_module, "AsyncOpenAI", FakeClient)

    result = await filter_module.filter_papers(
        {
            "user_query": "知识密集型问答",
            "research_plan": [
                {"retrieval_query": "retrieval augmented generation question answering"}
            ],
            "output_language": "zh-CN",
            "max_papers": 2,
            "raw_papers": [
                {
                    "paper_id": "paper-1",
                    "title": "Retrieval augmented generation for question answering",
                    "abstract": "Grounding with retrieval.",
                    "source": "arxiv",
                    "pdf_url": "https://example.test/1.pdf",
                },
                {
                    "paper_id": "paper-2",
                    "title": "Long context language models for question answering",
                    "abstract": "A comparison with retrieval augmented generation.",
                    "source": "semantic_scholar",
                    "pdf_url": "https://example.test/2.pdf",
                },
                {
                    "paper_id": "paper-3",
                    "title": "Unrelated manufacturing process study",
                    "abstract": "",
                    "source": "crossref",
                    "pdf_url": "",
                },
            ],
        }
    )

    assert [paper["paper_id"] for paper in result["selected_papers"]] == [
        "paper-1",
        "paper-2",
    ]
    assert "FILTER_FALLBACK_USED" in result["warnings"]
