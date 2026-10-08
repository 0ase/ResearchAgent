import json
from types import SimpleNamespace

import pytest

from backend.agents import filter as screening
from backend.agents.read import _merge_paper_insights
from backend.agents.search import deduplicate_papers, search_papers, select_candidate_papers
from backend.agents.search_review import SearchReviewDecision, review_search_results
from backend.agents.synthesize import _build_writer_messages
from backend.api.routes_research import _result_payload
from backend.config import Settings, settings
from backend.core.errors import AppError


def papers(count):
    return [{"source_id": f"p{i}", "title": f"Study {i}", "abstract": "a" * 1500,
             "published_date": "2025", "doi": f"10.123/p{i}",
             "source": "arxiv" if i % 2 else "crossref", "citation_count": i,
             "search_round_found": 1 + i % 3} for i in range(count)]


def score(number, *, topic=5, alignment=5, eligible=True):
    return {"paper_num": number, "eligible": eligible, "reason": "明确匹配原问题和研究任务",
            "scores": {"topic_match": topic, "question_alignment": alignment,
                       "methodology": 5, "evidence_quality": 5,
                       "recency": 5, "information_completeness": 5}}


def fake_client(monkeypatch, responder):
    async def create(**kwargs):
        request = json.loads(kwargs["messages"][1]["content"])
        text = responder(request, kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=text), finish_reason="stop")])
    monkeypatch.setattr(screening, "AsyncOpenAI", lambda **kwargs: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))


def test_pool_caps_at_100_and_merges_cross_source_duplicates():
    source = papers(120)
    duplicate = {**source[0], "source_id": "alternate-id", "doi": "", "abstract": ""}
    merged = deduplicate_papers([*source, duplicate])
    assert len(merged) == 120
    assert len(select_candidate_papers({"raw_papers": merged})["raw_papers"]) == 100
    assert len(select_candidate_papers({"raw_papers": papers(80)})["raw_papers"]) == 80


def test_insufficient_pool_reports_actual_count():
    with pytest.raises(AppError) as captured:
        select_candidate_papers({"raw_papers": papers(79)})
    assert captured.value.code == "SEARCH_TARGET_NOT_MET"
    assert "79" in captured.value.message and "80" in captured.value.message


def test_same_title_with_distinct_known_dois_is_not_merged():
    records = [{"title": "Shared title", "doi": "10.123/a"},
               {"title": "Shared title", "doi": "10.123/b"}]
    assert len(deduplicate_papers(records)) == 2


@pytest.mark.asyncio
async def test_below_80_forces_supplement_even_when_model_says_enough(monkeypatch):
    async def review(**kwargs):
        return SearchReviewDecision(action="enough", reason="覆盖足够", new_queries=[])
    monkeypatch.setattr("backend.agents.search_review.call_search_review_model", review)
    update = await review_search_results({
        "user_query": "world models for robotic control", "raw_papers": papers(70),
        "research_plan": [{"sub_query": "world models robotics"}], "search_round": 1,
    })
    assert update["search_review"]["action"] == "refine"
    assert len(update["research_plan"]) == 3


@pytest.mark.asyncio
async def test_search_obeys_cap_and_stops_after_round_budget(monkeypatch):
    calls = []
    async def source(query, **kwargs):
        calls.append(kwargs["max_results"])
        return papers(120)
    for name in ("search_arxiv", "search_semantic_scholar", "search_pubmed", "search_crossref"):
        monkeypatch.setattr(f"backend.agents.search.{name}", source)
    update = await search_papers({"research_plan": [{"sub_query": "world models"}], "search_round": 0})
    assert len(update["raw_papers"]) == 100
    assert calls == [20] * 4
    await search_papers({"research_plan": [{"sub_query": "world models"}],
                         "search_round": settings.max_search_rounds, "raw_papers": papers(100)})
    assert len(calls) == 4


@pytest.mark.asyncio
async def test_local_batch_ids_and_high_total_wrong_topic_are_handled(monkeypatch):
    def respond(request, kwargs):
        assert kwargs["max_tokens"] == settings.screening_max_tokens
        assert len(request["papers"][0]["abstract"]) == 1500
        assert request["papers"][0]["published_date"] == "2025"
        records = [score(p["paper_num"], topic=2 if p["title"] == "Study 0" else 5)
                   for p in request["papers"]]
        return json.dumps({"scores": records})
    fake_client(monkeypatch, respond)
    update = await screening.filter_papers({"user_query": "robotic world models",
                                           "raw_papers": papers(11), "max_papers": 15})
    selected_ids = {paper["source_id"] for paper in update["selected_papers"]}
    assert "p0" not in selected_ids
    assert "p10" in selected_ids
    rejected = next(paper for paper in update["raw_papers"] if paper["source_id"] == "p0")
    assert rejected["relevance_score"] == 79
    assert not rejected["screening_eligible"]
    assert update["screening_summary"]["selected"] == 10


@pytest.mark.asyncio
async def test_rejected_scope_constraint_is_not_overridden_by_high_scores(monkeypatch):
    fake_client(monkeypatch, lambda request, kwargs: json.dumps({
        "scores": [score(p["paper_num"], eligible=p["title"] != "Study 0") for p in request["papers"]]}))
    update = await screening.filter_papers({"user_query": "after 2023", "raw_papers": papers(2)})
    assert [paper["source_id"] for paper in update["selected_papers"]] == ["p1"]


@pytest.mark.asyncio
async def test_partial_output_retries_only_missing_record_and_ignores_duplicates(monkeypatch):
    calls = []
    def respond(request, kwargs):
        numbers = [paper["paper_num"] for paper in request["papers"]]
        calls.append(numbers)
        if len(calls) == 1:
            return json.dumps({"scores": [score(1), score(1), {"paper_num": 2, "score": 5}]})
        return json.dumps({"scores": [score(2)]})
    fake_client(monkeypatch, respond)
    update = await screening.filter_papers({"user_query": "question", "raw_papers": papers(2)})
    assert calls == [[1, 2], [2]]
    assert len(update["selected_papers"]) == 2
    assert len({paper["source_id"] for paper in update["selected_papers"]}) == 2


@pytest.mark.asyncio
async def test_empty_output_and_no_relevant_evidence_are_distinct_errors(monkeypatch):
    fake_client(monkeypatch, lambda request, kwargs: "")
    with pytest.raises(AppError) as empty:
        await screening.filter_papers({"user_query": "question", "raw_papers": papers(1)})
    assert empty.value.code == "SCREENING_FAILED"
    fake_client(monkeypatch, lambda request, kwargs: json.dumps({"scores": [score(1, alignment=1)]}))
    with pytest.raises(AppError) as unrelated:
        await screening.filter_papers({"user_query": "question", "raw_papers": papers(1)})
    assert unrelated.value.code == "NO_RELEVANT_PAPERS"


def test_excluded_old_evidence_does_not_reenter_reading_or_writer():
    selected = [{"source_id": "current", "title": "Relevant study"}]
    old = [{"source": "rejected", "answer": "Unrelated clinical evidence"}]
    fresh = [{"source": "current", "answer": "Relevant robotic evidence"}]
    merged = _merge_paper_insights(selected, old, fresh, 15)
    assert merged == fresh
    messages = _build_writer_messages({"user_query": "question", "selected_papers": selected,
                                      "paper_insights": [*old, *fresh]})
    assert "Unrelated clinical evidence" not in messages[1]["content"]
    assert "Relevant robotic evidence" in messages[1]["content"]


def test_result_preserves_multidimensional_scores_and_selected_papers():
    scored = screening._scored_paper(papers(1)[0], screening.ScreeningScore.model_validate(score(1)))
    payload = _result_payload({"raw_papers": [scored], "selected_papers": [scored],
                               "screening_summary": {"selected": 1}})
    assert payload["selected_papers"][0]["relevance_score_scale"] == 100
    assert payload["papers"][0]["screening_scores"]["topic_match"] == 5
    assert payload["screening_summary"]["selected"] == 1


def test_candidate_minimum_cannot_exceed_maximum():
    with pytest.raises(ValueError):
        Settings(_env_file=None, min_candidate_papers=100, max_candidate_papers=80)
