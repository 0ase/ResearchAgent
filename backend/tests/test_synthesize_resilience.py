from types import SimpleNamespace

import pytest

import backend.agents.synthesize as synthesize_module


@pytest.mark.asyncio
async def test_synthesize_replaces_citation_only_provider_output(monkeypatch) -> None:
    class FakeCompletions:
        async def create(self, **_kwargs):
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content='{"report":"[[CITE:placeholder]]"}'
                        )
                    )
                ]
            )

    class FakeClient:
        def __init__(self, **_kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr(synthesize_module, "AsyncOpenAI", FakeClient)

    result = await synthesize_module.synthesize_review(
        {
            "user_query": "比较两种方法",
            "output_language": "zh-CN",
            "paper_insights": [
                {"paper_id": "paper-1", "answer": "摘要证据"},
            ],
            "paper_claims": [
                {
                    "claim_id": "claim-1",
                    "paper_id": "paper-1",
                    "statement": "检索可以改善知识密集型问答的事实性。",
                    "chunk_ids": ["chunk-1"],
                }
            ],
        }
    )

    assert result["final_answer"].startswith("# 研究综合报告")
    assert "检索可以改善" in result["final_answer"]
    assert "[[CITE:" in result["final_answer"]
    assert result["structured_report"]["citations"][0]["claim_ids"] == ["claim-1"]
