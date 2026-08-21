from types import SimpleNamespace

import pytest

import backend.agents.orchestrator as orchestrator


def test_parse_structured_query_plan_keeps_display_and_retrieval_queries() -> None:
    plan = orchestrator._normalize_query_plan(
        [
            {
                "display_query": "检索增强生成的事实性评估",
                "retrieval_query": "retrieval augmented generation factuality evaluation",
            }
        ],
        output_language="zh-CN",
    )

    assert plan == [
        {
            "display_query": "检索增强生成的事实性评估",
            "retrieval_query": "retrieval augmented generation factuality evaluation",
        }
    ]


def test_legacy_string_plan_marks_chinese_retrieval_as_missing() -> None:
    plan = orchestrator._normalize_query_plan(
        ["检索增强生成的事实性评估"],
        output_language="zh-CN",
    )

    assert plan == [
        {
            "display_query": "检索增强生成的事实性评估",
            "retrieval_query": "",
        }
    ]


def test_legacy_english_plan_can_be_reused_for_display_and_retrieval() -> None:
    plan = orchestrator._normalize_query_plan(
        ["retrieval augmented generation factuality evaluation"],
        output_language="en",
    )

    assert plan == [
        {
            "display_query": "retrieval augmented generation factuality evaluation",
            "retrieval_query": "retrieval augmented generation factuality evaluation",
        }
    ]


@pytest.mark.asyncio
async def test_orchestrate_completes_missing_chinese_retrieval_queries(monkeypatch) -> None:
    responses = iter(
        [
            '[{"display_query":"检索增强生成的事实性评估","retrieval_query":""}]',
            '["retrieval augmented generation factuality evaluation"]',
        ]
    )

    class FakeCompletions:
        async def create(self, **_kwargs):
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=next(responses)),
                    )
                ]
            )

    class FakeClient:
        def __init__(self, **_kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(orchestrator, "AsyncOpenAI", FakeClient)

    result = await orchestrator.orchestrate(
        {
            "user_query": "分析 RAG 的事实性",
            "output_language": "zh-CN",
        }
    )

    assert result["research_plan"] == [
        {
            "sub_query": "检索增强生成的事实性评估",
            "display_query": "检索增强生成的事实性评估",
            "retrieval_query": "retrieval augmented generation factuality evaluation",
            "status": "pending",
        }
    ]
    assert result["search_round"] == 1
