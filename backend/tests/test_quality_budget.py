import pytest
from langgraph.graph import StateGraph, START, END

from backend.agents.state import ResearchState
from backend.agents.contracts import SupervisorDecision
from backend.agents.policy import validate_decision
from backend.agents.supervisor import _decision_command, supervisor
from backend.agents.graph import finish
from backend.domain.errors import ResearchPipelineError
from backend.services.result_builder import build_result, validate_result_ready
from backend.tests.evidence_fixture import evidence_state


@pytest.mark.parametrize("extra,expected", [
    ({}, "finish"),
    ({"paper_insights": [{}]}, "analysis"),
    ({"paper_insights": [{}], "analysis_report": {"agreements": []}}, "writer"),
    ({"paper_insights": [{}], "analysis_report": {"agreements": []}, "draft_sections": [{}]}, "critic"),
    ({"paper_insights": [{}], "draft_sections": [{}], "critique": {"approved": True}}, "finish"),
])
def test_budget_routes_are_deterministic(extra, expected):
    state = {"step_count": 12, "max_steps": 12, **extra}
    decision = SupervisorDecision(next_agent="retrieval", objective="search", reason="search")
    assert validate_decision(decision, state).next_agent == expected


@pytest.mark.asyncio
async def test_budget_finishes_in_three_delegations_without_supervisor_calls(monkeypatch):
    import importlib
    module = importlib.import_module("backend.agents.supervisor")
    monkeypatch.setattr(module, "AsyncOpenAI", lambda **kw: pytest.fail("Budget gate must precede provider creation"))
    state = {"paper_insights": [{}], "step_count": 12, "max_steps": 12}
    for target, output in [("analysis", {"analysis_report": {"agreements": []}}),
                           ("writer", {"draft_sections": [{"content": "Report"}]}),
                           ("critic", {"critique": {"approved": False}, "critique_round": 1})]:
        command = await supervisor(state)
        assert command.goto == target
        state.update(command.update)
        state.update(output)
    command = await supervisor(state)
    assert command.goto == "finish"
    assert command.update["step_count"] == 15


@pytest.mark.parametrize("critique", [None, {}, {"approved": False}])
def test_unapproved_results_are_partial(critique):
    result = build_result("t", {**evidence_state(), "critique": critique})
    validate_result_ready(result)
    assert result.partial and "CRITIQUE_NOT_APPROVED" in result.warnings


def test_finish_does_not_promote_raw_paper_text():
    with pytest.raises(ResearchPipelineError):
        finish({"raw_papers": [{"title": "Title", "abstract": "Abstract"}]})
    with pytest.raises(ResearchPipelineError, match="报告"):
        finish({"paper_insights": [{"answer": "Read excerpt"}], "final_answer": "Read excerpt"})


@pytest.mark.asyncio
async def test_warning_union_survives_nested_graph_reentry():
    child = StateGraph(ResearchState)
    child.add_node("read", lambda state: {"warnings": ["READ_FALLBACK", "SOURCE_FAILED"]})
    child.add_edge(START, "read"); child.add_edge("read", END)
    parent = StateGraph(ResearchState)
    parent.add_node("retrieval1", child.compile()); parent.add_node("retrieval2", child.compile())
    parent.add_edge(START, "retrieval1"); parent.add_edge("retrieval1", "retrieval2"); parent.add_edge("retrieval2", END)
    state = await parent.compile().ainvoke({"warnings": ["SOURCE_FAILED"]})
    assert state["warnings"] == ["SOURCE_FAILED", "READ_FALLBACK"]


def test_result_without_evidence_is_rejected():
    state = evidence_state()
    state["chunks"] = []
    with pytest.raises(ResearchPipelineError) as error:
        validate_result_ready(build_result("t", state))
    assert error.value.code == "NO_VERIFIABLE_EVIDENCE"


@pytest.mark.asyncio
async def test_two_reviews_remain_exhausted_after_draft_invalidation(monkeypatch):
    import importlib
    module = importlib.import_module("backend.agents.supervisor")
    monkeypatch.setattr(module, "AsyncOpenAI", lambda **kw: pytest.fail("No third review or provider decision"))
    command = await supervisor({"step_count": 9, "paper_insights": [{}],
                                "draft_sections": [{"content": "Revised"}],
                                "critique": None, "critique_round": 2})
    assert command.goto == "finish"


@pytest.mark.parametrize("markdown", ["# Report [[CITE:citation-1]]", "A tiny answer.", "[[CITE:citation-1]]" * 20])
def test_result_builder_independently_rejects_non_substantive_body(markdown):
    state = {**evidence_state(), "final_answer": markdown}
    with pytest.raises(ResearchPipelineError) as error:
        validate_result_ready(build_result("t", state))
    assert error.value.code == "EMPTY_REPORT"


def test_result_builder_rejects_empty_insight_objects():
    state = {**evidence_state(), "paper_insights": [{}]}
    with pytest.raises(ResearchPipelineError) as error:
        validate_result_ready(build_result("t", state))
    assert error.value.code == "NO_READABLE_PAPERS"


@pytest.mark.asyncio
async def test_critic_timeout_keeps_verified_report_partial(monkeypatch):
    from types import SimpleNamespace
    import backend.agents.critic as critic
    async def timeout(**kwargs):
        raise TimeoutError("injected provider timeout")
    monkeypatch.setattr(critic, "AsyncOpenAI", lambda **kwargs: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=timeout))))
    state = {**evidence_state(), "step_count": 9, "critique_round": 0}
    state.update(await critic.critique_output(state))
    command = await supervisor(state)
    assert command.goto == "finish"
    result = build_result("t", {**state, **finish(state)})
    validate_result_ready(result)
    assert result.partial and not result.critique["approved"]
    assert "CRITIQUE_NOT_APPROVED" in result.warnings


@pytest.mark.asyncio
@pytest.mark.parametrize("issue_type,issues,expected", [
    ("none", ["Missing independent baselines"], False),
    ("analysis_gap", [], False), ("none", [], True),
])
async def test_critic_approval_requires_consistent_provider_fields(monkeypatch, issue_type, issues, expected):
    import json
    from types import SimpleNamespace
    import backend.agents.critic as critic
    async def complete(*args, **kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({
            "approved": True, "score": 7 if issues else 9, "issue_type": issue_type,
            "issues": issues, "feedback": "Keep this feedback"})))])
    monkeypatch.setattr(critic, "AsyncOpenAI", lambda **kwargs: object())
    monkeypatch.setattr(critic, "chat_completion", complete)
    monkeypatch.setattr(critic, "find_report_completeness_issues", lambda *args: [])
    state = {**evidence_state(), "critique_round": 0}
    state["structured_report"]["sections"][0].update(heading="Report", level=1, markdown=state["final_answer"])
    for number in (1, 2):
        state.update(await critic.critique_output(state))
        assert state["approved"] is expected
        assert state["critique_round"] == number
        if not expected:
            assert state["critique"]["issues"] == issues
            assert state["critique"]["issue_type"] == issue_type
            assert state["critique"]["feedback"] == "Keep this feedback"
    result = build_result("t", state)
    if not expected:
        assert result.partial and "CRITIQUE_NOT_APPROVED" in result.warnings
    assert validate_decision(SupervisorDecision(next_agent="critic", objective="review", reason="review"), state).next_agent == "finish"


@pytest.mark.asyncio
async def test_critic_cannot_approve_without_deterministic_evidence_review(monkeypatch):
    from types import SimpleNamespace
    import backend.agents.critic as critic
    async def complete(*args, **kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=
            '{"approved":true,"score":10,"issue_type":"none","issues":[],"feedback":""}'))])
    monkeypatch.setattr(critic, "AsyncOpenAI", lambda **kwargs: object())
    monkeypatch.setattr(critic, "chat_completion", complete)
    monkeypatch.setattr(critic, "find_report_completeness_issues", lambda *args: [])
    state = evidence_state()
    state.pop("structured_report")
    result = await critic.critique_output(state)
    assert result["approved"] is False
