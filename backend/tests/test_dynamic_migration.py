import asyncio
from datetime import datetime, timezone

import pytest
from langgraph.types import Command
from backend.agents import graph, retrieval_graph
from backend.api.schemas.tasks import TaskSnapshot, TaskStatus
from backend.db.connection import open_database
from backend.db.migrate import migrate_database
from backend.repositories.task_repository import TaskRepository
from backend.repositories.event_repository import EventRepository
from backend.services.event_recorder import EventRecorder
from backend.services.task_runner import TaskRunner
from backend.services.result_builder import build_result
from backend.agents.synthesize import _length_instruction
from backend.agents.instrumentation import safe_text
from backend.config import settings


def test_writer_length_follows_explicit_locale_and_trace_redacts_before_truncation(monkeypatch):
    assert "words" in _length_instruction("中文问题", "en")
    assert "中文字符" in _length_instruction("English question", "zh-CN")
    monkeypatch.setattr(settings, "deepseek_api_key", "private-test-key")
    assert "private" not in safe_text("a" * 1995 + "private-test-key")


@pytest.mark.asyncio
async def test_real_compiled_graph_retains_subgraph_state_and_repeated_stage_attempts(tmp_path, monkeypatch):
    path = tmp_path / "dynamic.db"
    await migrate_database(path)
    factory = lambda: open_database(path)
    tasks = TaskRepository(factory)
    events = EventRecorder(EventRepository(factory))
    task = TaskSnapshot(id="dynamic",client_request_id="r1",query="Research question",title="Title",
        status=TaskStatus.RUNNING,created_at=datetime.now(timezone.utc),options={"max_papers":3,"sources":["arxiv"],"output_language":"en"})
    await tasks.create(task)
    async def supervisor(state):
        sequence = ["retrieval", "analysis", "writer", "critic", "writer", "critic", "finish"]
        step = state.get("step_count",0)
        target = sequence[step]
        return Command(goto=target,update={"step_count":step+1,"next_agent":target,"current_task":"Objective","decision_reason":"Reason"})
    async def plan(state):
        assert state["sources"] == ["arxiv"]
        return {"research_plan":[{"sub_query":"query"}]}
    async def search(state):
        return {"raw_papers":[{"paper_id":"p1","source_id":"p1","title":"Paper"}],"search_round":state.get("search_round",0)+1}
    async def review(state):
        return {"search_review":{"action":"refine" if state["search_round"] == 1 else "enough"}}
    async def select(state):
        return {"selected_papers":state["raw_papers"]}
    async def read(state):
        return {"paper_insights":[{"source":"p1","paper_id":"p1","answer":"Real evidence excerpt"}],
            "paper_claims":[{"claim_id":"claim-1","paper_id":"p1","statement":"Evidence", "chunk_ids":["chunk-1"]}],
            "chunks":[{"chunk_id":"chunk-1","paper_id":"p1","content":"Real evidence excerpt"}]}
    async def analysis(state):
        assert state["chunks"][0]["chunk_id"] == "chunk-1"
        return {"analysis_report":{"agreements":["Evidence agreement"]},"analysis_findings":[]}
    async def writer(state):
        return {"draft_sections":[{"content":"The report compares the supplied source evidence with the research question and explains the limits of this observation. The evidence does not justify claims beyond the available source text."}],"final_answer":"The report compares the supplied source evidence with the research question and explains the limits of this observation. The evidence does not justify claims beyond the available source text.","writer_generation_attempts":2,"writer_incomplete":False}
    async def critic(state):
        number=state.get("critique_round",0)+1
        return {"critique_round":number,"critique":{"score":8,"approved":number==2},"critique_history":[{"round":number}]}
    for module,name,node in [(graph,"supervisor",supervisor),(graph,"analyze_papers",analysis),(graph,"synthesize_review",writer),(graph,"critique_output",critic),
        (retrieval_graph,"orchestrate",plan),(retrieval_graph,"search_papers",search),(retrieval_graph,"review_search_results",review),(retrieval_graph,"filter_papers",select),(retrieval_graph,"read_papers",read)]:
        monkeypatch.setattr(module,name,node)
    state = await TaskRunner(event_recorder=events).run(task,asyncio.Event())
    assert len(state["agent_trace"]) == 7
    assert state["search_round"] == 2
    assert [item["round"] for item in state["critique_history"]] == [1,2]
    assert len(state["chunks"]) == 1
    result=build_result(task.id,state,supports_replay=True)
    assert result.run_metadata["writer_generation_attempts"] == 2
    snapshot=await tasks.get(task.id)
    assert snapshot.last_sequence == snapshot.replay_events[-1]["sequence"]
    assert next(stage for stage in snapshot.stages if stage.stage == "synthesize").attempt == 2
    assert next(stage for stage in snapshot.stages if stage.stage == "search").attempt == 4
