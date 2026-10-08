"""Behavioral checks for priority ordering, stop conditions and failed scoring."""
import json
from types import SimpleNamespace

import pytest

from backend.agents import filter as screening
from backend.api.routes_research import _result_payload
from backend.config import Settings, settings
from backend.services.paper_ranking import citation_count, rank_candidate_papers
from backend.sources.arxiv_client import parse_arxiv_response
from backend.sources.crossref_client import _parse_response as parse_crossref
from backend.sources.pubmed_client import _parse_pubmed_response
from backend.sources.semantic_scholar_client import _parse_response as parse_s2
from frontend.components.progress import stage_detail_filter


def candidates(count):
    return [{"source_id": f"p{i}", "title": f"Robotic world model study {i}",
             "abstract": "Robotic world models predict actions and observations.",
             "source": "arxiv", "published_date": "2025", "citation_count_known": False}
            for i in range(count)]


def record(number, *, level=4, core=4, eligible=True):
    return {"paper_num": number, "eligible": eligible, "reason": "与原问题匹配",
            "scores": {"topic_match": core, "question_alignment": core,
                       "methodology": level, "evidence_quality": level,
                       "recency": level, "information_completeness": level}}


def client(monkeypatch, responder):
    calls = []
    async def create(**kwargs):
        request = json.loads(kwargs["messages"][1]["content"])
        calls.append(request["papers"])
        assert kwargs["max_tokens"] == 6000
        text, reason = responder(request, len(calls))
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=text, reasoning_content=""), finish_reason=reason)],
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=6000,
                                  total_tokens=6100, completion_tokens_details=SimpleNamespace(reasoning_tokens=5000)))
    monkeypatch.setattr(screening, "AsyncOpenAI", lambda **kwargs: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    monkeypatch.setattr(settings, "screening_batch_size", 5)
    monkeypatch.setattr(settings, "screening_max_tokens", 6000)
    monkeypatch.setattr(settings, "screening_min_score", 70)
    monkeypatch.setattr(settings, "screening_supplement_min_score", 65)
    return calls


@pytest.mark.asyncio
async def test_stops_at_user_target_without_submitting_remaining_candidates(monkeypatch):
    calls = client(monkeypatch, lambda request, n: (
        json.dumps({"scores": [record(p["paper_num"]) for p in request["papers"]]}), "stop"))
    update = await screening.filter_papers({"user_query": "robotic world models", "raw_papers": candidates(93),
                                           "max_papers": 7})
    summary = update["screening_summary"]
    assert [len(batch) for batch in calls] == [5, 5]
    assert summary["selected"] == summary["target"] == 7
    assert summary["scored"] == summary["attempted"] == 10
    assert summary["not_evaluated"] == 83 and summary["failed"] == 0
    assert summary["stopped_early"] and "errors" not in update
    pending = [p for p in update["raw_papers"] if p["screening_status"] == "not_evaluated"]
    assert len(pending) == 83 and all(p["relevance_score"] is None for p in pending)
    payload = _result_payload(update)
    assert payload["papers"][-1]["screening_eligible"] is None
    detail = stage_detail_filter({"summary": summary, "count": 7})
    assert "未评估 83" in detail and "评分失败" not in detail


@pytest.mark.asyncio
async def test_rescreening_does_not_retain_error_ids_from_previous_attempts(monkeypatch):
    client(monkeypatch, lambda request, n: (
        json.dumps({"scores": [record(p["paper_num"]) for p in request["papers"]]}), "stop"))
    source = [{**paper, "screening_status": "failed", "screening_error_id": "previous-error"}
              for paper in candidates(10)]
    update = await screening.filter_papers({"user_query": "robotic world models", "raw_papers": source,
                                           "max_papers": 3})
    assert all(p["screening_error_id"] is None for p in update["raw_papers"])
    assert update["screening_summary"]["failed"] == 0


@pytest.mark.asyncio
async def test_truncated_json_recovers_complete_scores_and_splits_only_missing(monkeypatch):
    def respond(request, n):
        numbers = [p["paper_num"] for p in request["papers"]]
        if n == 1:
            return '{"scores":[' + json.dumps(record(numbers[0])) + ',{"paper_num":2,', "length"
        return json.dumps({"scores": [record(number) for number in numbers]}), "stop"
    calls = client(monkeypatch, respond)
    update = await screening.filter_papers({"user_query": "robotic world models", "raw_papers": candidates(8),
                                           "max_papers": 5})
    assert [[p["paper_num"] for p in batch] for batch in calls] == [[1, 2, 3, 4, 5], [2, 3], [4, 5]]
    assert update["screening_summary"]["selected"] == 5
    assert update["screening_summary"]["failed"] == 0
    assert update["screening_summary"]["not_evaluated"] == 3


@pytest.mark.asyncio
async def test_failed_records_remain_distinct_from_unsubmitted_records(monkeypatch):
    def respond(request, n):
        if n <= 4:
            return "", "length"
        return json.dumps({"scores": [record(p["paper_num"]) for p in request["papers"]]}), "stop"
    calls = client(monkeypatch, respond)
    update = await screening.filter_papers({"user_query": "robotic world models", "raw_papers": candidates(15),
                                           "max_papers": 5})
    assert [len(batch) for batch in calls] == [5, 2, 2, 1, 5]
    summary = update["screening_summary"]
    assert summary["failed"] == 5 and summary["not_evaluated"] == 5
    assert summary["scored"] == summary["selected"] == 5
    assert "5 篇候选论文评分失败" in update["errors"][0]


@pytest.mark.asyncio
async def test_borderline_papers_wait_until_all_candidates_and_retries_are_exhausted(monkeypatch):
    def respond(request, n):
        # 3/5 on all dimensions yields 60; core 4 and other dimensions 2.5 yields 68.
        return json.dumps({"scores": [record(p["paper_num"], level=2.5 if n == 1 else 4)
                                      for p in request["papers"]]}), "stop"
    calls = client(monkeypatch, respond)
    update = await screening.filter_papers({"user_query": "robotic world models", "raw_papers": candidates(10),
                                           "max_papers": 7})
    assert len(calls) == 2
    summary = update["screening_summary"]
    assert summary["qualified_primary"] == 5 and summary["supplemented"] == 2
    assert summary["not_evaluated"] == 0 and summary["selected"] == 7
    assert [p["screening_tier"] for p in update["selected_papers"]] == ["standard"] * 5 + ["supplemental"] * 2
    assert all(p["relevance_score"] == 68 for p in update["selected_papers"][5:])


@pytest.mark.asyncio
async def test_early_borderline_matches_do_not_stop_search_for_standard_matches(monkeypatch):
    def respond(request, n):
        return json.dumps({"scores": [record(p["paper_num"], level=2.5 if n == 1 else 4)
                                      for p in request["papers"]]}), "stop"
    calls = client(monkeypatch, respond)
    update = await screening.filter_papers({"user_query": "robotic world models", "raw_papers": candidates(15),
                                           "max_papers": 5})
    assert len(calls) == 2
    summary = update["screening_summary"]
    assert summary["selected"] == 5 and summary["supplemented"] == 0
    assert summary["not_evaluated"] == 5
    assert all(p["screening_tier"] == "standard" for p in update["selected_papers"])


@pytest.mark.asyncio
async def test_unrelated_or_wrong_scope_papers_cannot_fill_target_after_relaxation(monkeypatch):
    def respond(request, n):
        rows = []
        for p in request["papers"]:
            if p["title"].endswith("0"):
                rows.append(record(p["paper_num"]))
            elif p["title"].endswith("1"):
                rows.append(record(p["paper_num"], level=5, core=2))
            else:
                rows.append(record(p["paper_num"], eligible=False))
        return json.dumps({"scores": rows}), "stop"
    client(monkeypatch, respond)
    update = await screening.filter_papers({"user_query": "robotic world models", "raw_papers": candidates(3),
                                           "max_papers": 3})
    assert [p["source_id"] for p in update["selected_papers"]] == ["p0"]
    assert update["screening_summary"]["supplemented"] == 0
    assert "目标阅读 3 篇" in update["errors"][0]


def test_priority_applies_below_cap_and_topic_beats_unrelated_prestige(monkeypatch, tmp_path):
    path = tmp_path / "metrics.json"
    path.write_text(json.dumps({"Known Journal": {"score": 100, "year": 2025,
                           "source": "https://example.org/verified-metric", "metric": "user-supplied ranking"}}))
    monkeypatch.setattr(settings, "venue_quality_path", str(path))
    ranked = rank_candidate_papers([
        {"title": "Robotic world models", "abstract": "Robotic world models", "source_id": "relevant"},
        {"title": "Clinical diagnosis", "abstract": "Clinical diagnosis", "source_id": "unrelated",
         "venue": "Known Journal", "citation_count": 10000, "pdf_url": "https://example.org/a.pdf"}],
        "robotic world models")
    assert ranked[0]["source_id"] == "relevant"
    assert ranked[0]["venue_quality"] is None
    assert ranked[1]["venue_quality"]["score"] == 100


def test_unknown_citations_and_unsupported_venue_metrics_are_not_fabricated():
    assert citation_count({"source": "pubmed", "citation_count": 0}) is None
    assert citation_count({"source": "semantic_scholar", "citation_count": 0, "citation_count_known": True}) == 0
    ranked = rank_candidate_papers([{"title": "study", "citation_count_known": False,
                                    "venue_quality": {"score": 100}}], "study")
    assert ranked[0]["candidate_priority_details"]["citations"] == 0.5
    assert ranked[0]["venue_quality"] is None


def test_metadata_parsers_keep_venue_date_pdf_and_missing_citation_semantics():
    s2 = parse_s2({"data": [{"title": "Study", "citationCount": 0,
                            "publicationVenue": {"name": "Venue", "issn": "1234-5678"}}]})[0]
    assert s2["venue"] == "Venue" and s2["issns"] == ["1234-5678"] and s2["citation_count_known"]
    cr = parse_crossref({"message": {"items": [{"title": ["Study"], "container-title": ["Journal"],
                        "ISSN": ["1234-5678"], "link": [{"content-type": "application/pdf", "URL": "https://example.org/a.pdf"}]}]}})[0]
    assert cr["venue"] == "Journal" and cr["pdf_url"] and not cr["citation_count_known"]
    pm = _parse_pubmed_response('<PubmedArticleSet><PubmedArticle><MedlineCitation><Article>'
         '<ArticleTitle>Study</ArticleTitle><Journal><Title>Journal</Title><ISSN>1234-5678</ISSN>'
         '<JournalIssue><PubDate><Year>2025</Year></PubDate></JournalIssue></Journal>'
         '</Article></MedlineCitation></PubmedArticle></PubmedArticleSet>')[0]
    assert pm["published_date"] == "2025" and pm["venue"] == "Journal" and not pm["citation_count_known"]
    ax = parse_arxiv_response('<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Study</title>'
                             '<published>2025-01-01</published></entry></feed>')[0]
    assert ax["published_date"] == "2025-01-01" and not ax["citation_count_known"]


def test_invalid_supplement_threshold_is_rejected():
    with pytest.raises(ValueError):
        Settings(_env_file=None, screening_min_score=70, screening_supplement_min_score=75)
