import pytest

from backend.agents.contracts import SupervisorDecision
from backend.agents.orchestrator import _ensure_sub_queries
from backend.agents.policy import validate_decision
from backend.agents.retrieval_graph import route_after_review
from backend.agents.search import search_papers, select_candidate_papers
from backend.agents.search_review import (
    SearchReviewDecision,
    review_search_results,
)
from backend.agents.supervisor import supervisor
from backend.agents.synthesize import _build_writer_messages
from backend.config import settings
from backend.services.chunking import chunk_text


def test_single_planned_query_is_expanded_to_multiple_search_angles():
    original = "比较降低大语言模型幻觉的方法"

    result = _ensure_sub_queries(["LLM hallucination mitigation"], original)

    assert 3 <= len(result) <= 5
    assert len({query.casefold() for query in result}) == len(result)
    assert any(original in query for query in result)


def test_writer_prompt_requires_thematic_synthesis():
    messages = _build_writer_messages({
        "user_query": "比较方法 A 和方法 B",
        "current_task": "撰写综合综述",
        "selected_papers": [
            {"source_id": "p1", "title": "First Study"},
            {"source_id": "p2", "title": "Second Study"},
        ],
        "paper_insights": [
            {"source": "p1", "answer": "Method A improves accuracy."},
            {"source": "p2", "answer": "Method B reduces cost."},
        ],
        "analysis_report": {"agreements": [], "contradictions": []},
    })

    system_prompt = messages[0]["content"]
    user_prompt = messages[1]["content"]
    assert "thematic synthesis" in system_prompt
    assert "Do NOT create one heading or paragraph per paper" in system_prompt
    assert "[Source p1]" in user_prompt
    assert "[Source p2]" in user_prompt
    assert "### Paper 1" not in user_prompt


@pytest.mark.parametrize("requested_agent", ["retrieval", "analysis", "writer", "critic"])
def test_approved_draft_forces_finish(requested_agent):
    decision = SupervisorDecision(
        next_agent=requested_agent,
        objective="run another agent",
        reason="model requested another round",
    )
    state = {
        "step_count": 5,
        "max_steps": 12,
        "draft_sections": [{"content": "approved review"}],
        "critique": {"score": 9, "approved": True, "issue_type": "none"},
    }

    safe = validate_decision(decision, state)

    assert safe.next_agent == "finish"


@pytest.mark.asyncio
async def test_supervisor_skips_llm_after_first_approval(monkeypatch):
    def fail_if_client_is_created(*args, **kwargs):
        raise AssertionError("Supervisor LLM must not run after approval")

    monkeypatch.setattr(
        "backend.agents.supervisor.AsyncOpenAI",
        fail_if_client_is_created,
    )
    command = await supervisor({
        "step_count": 5,
        "max_steps": 12,
        "draft_sections": [{"content": "approved review"}],
        "final_answer": "approved review",
        "critique": {"score": 9, "approved": True, "issue_type": "none"},
    })

    assert command.goto == "finish"
    assert command.update["step_count"] == 6


@pytest.mark.asyncio
async def test_refined_queries_replace_plan_before_second_search(monkeypatch):
    old_queries = ["old broad query", "old methods query"]
    new_queries = ["new benchmark query", "new limitations query"]

    async def fake_review_model(**kwargs):
        assert kwargs["current_queries"] == old_queries
        return SearchReviewDecision(
            action="refine",
            reason="存在关键证据缺口",
            missing_topics=["benchmark", "limitations"],
            new_queries=new_queries,
        )

    monkeypatch.setattr(
        "backend.agents.search_review.call_search_review_model",
        fake_review_model,
    )
    state = {
        "user_query": "original question",
        "research_plan": [
            {"sub_query": query, "status": "pending"}
            for query in old_queries
        ],
        "raw_papers": [{"title": "Existing paper", "source_id": "p0"}],
        "previous_queries": [],
        "search_round": 1,
    }

    update = await review_search_results(state)
    updated_state = {**state, **update}

    assert route_after_review(updated_state) == "refine"
    assert [item["sub_query"] for item in updated_state["research_plan"]] == new_queries

    searched_queries: list[str] = []

    async def fake_source(query, **kwargs):
        searched_queries.append(query)
        return []

    for source_name in (
        "search_arxiv",
        "search_semantic_scholar",
        "search_pubmed",
        "search_crossref",
    ):
        monkeypatch.setattr(
            f"backend.agents.search.{source_name}",
            fake_source,
        )

    await search_papers(updated_state)

    assert set(searched_queries) == set(new_queries)
    assert not set(old_queries).intersection(searched_queries)


def test_candidate_pool_preserves_refined_round(monkeypatch):
    monkeypatch.setattr(settings, "max_candidate_papers", 4)
    papers = []
    for round_number in (1, 2):
        for source in ("arxiv", "crossref"):
            for index in range(3):
                papers.append({
                    "title": f"round-{round_number}-{source}-{index}",
                    "source": source,
                    "source_id": f"{round_number}-{source}-{index}",
                    "search_round_found": round_number,
                    "abstract": "evidence",
                    "citation_count": index,
                })

    update = select_candidate_papers({"raw_papers": papers})
    selected = update["raw_papers"]

    assert len(selected) == 4
    assert {paper["search_round_found"] for paper in selected} == {1, 2}
    assert {paper["source"] for paper in selected} == {"arxiv", "crossref"}


@pytest.mark.asyncio
async def test_retrieval_exhaustion_finishes_without_supervisor_llm(monkeypatch):
    def fail_if_client_is_created(*args, **kwargs):
        raise AssertionError("Supervisor must not retry an exhausted retrieval")

    monkeypatch.setattr(
        "backend.agents.supervisor.AsyncOpenAI",
        fail_if_client_is_created,
    )
    command = await supervisor({
        "step_count": 1,
        "max_steps": 12,
        "retrieval_exhausted": True,
        "paper_insights": [],
    })

    assert command.goto == "finish"


def test_chunk_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        chunk_text("sample text", chunk_size=100, overlap=100)


def test_rejected_draft_stops_at_critique_round_limit():
    decision = SupervisorDecision(
        next_agent="writer",
        objective="revise again",
        reason="critic rejected the draft",
    )
    state = {
        "draft_sections": [{"content": "best available draft"}],
        "paper_insights": [{"answer": "evidence"}],
        "analysis_report": {"agreements": []},
        "critique": {"approved": False, "score": 6},
        "critique_round": settings.max_critique_rounds,
    }

    safe = validate_decision(decision, state)

    assert safe.next_agent == "finish"
