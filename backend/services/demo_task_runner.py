from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from typing import Any

from backend.api.schemas.events import EventLevel, EventType
from backend.api.schemas.tasks import ResearchStage, TaskSnapshot
from backend.services.paper_normalizer import normalize_papers


class DemoTaskRunner:
    """Deterministic, network-free runner used by local development and E2E tests."""

    def __init__(
        self,
        *,
        event_recorder: object,
        delay_seconds: float = 0.0,
        critic_revisions: bool = True,
    ) -> None:
        self._event_recorder = event_recorder
        self._delay_seconds = max(0.0, delay_seconds)
        self._critic_revisions = critic_revisions

    async def run(self, task: TaskSnapshot, cancel_event: asyncio.Event) -> dict[str, Any]:
        locale = task.effective_locale
        options = task.options or {}
        sources = set(options.get("sources") or ["arxiv", "semantic_scholar", "pubmed", "crossref"])
        source_warning_active = "crossref" in sources
        max_papers = max(1, int(options.get("max_papers", 20)))
        papers = [
            paper.to_result_dict()
            for paper in normalize_papers(_demo_papers(locale), task_id=task.id)
            if paper.source in sources
        ][:max_papers]
        selected = [
            paper
            for paper in papers
            if paper.get("full_text_status") != "unavailable"
        ][: min(4, max_papers)]
        if not papers:
            raise RuntimeError("demo sources returned no papers")
        plan = [
            {"step": 1, "title": _demo_text(locale, "plan_question"), "status": "complete"},
            {"step": 2, "title": _demo_text(locale, "plan_compare"), "status": "complete"},
            {"step": 3, "title": _demo_text(locale, "plan_synthesize"), "status": "complete"},
        ]
        insights = [
            {
                "paper_id": paper["paper_id"],
                "answer": _demo_text(locale, "insight", title=paper["title"]),
            }
            for paper in selected
        ]
        evidence_excerpt = _demo_text(locale, "evidence")
        claim = {
            "claim_id": "demo-claim-1",
            "paper_id": papers[0]["paper_id"],
            "statement": _demo_text(locale, "claim"),
            "chunk_ids": ["demo-chunk-1"],
            "support_type": "direct",
        }
        chunks = [{
            "chunk_id": "demo-chunk-1",
            "paper_id": papers[0]["paper_id"],
            "content": evidence_excerpt,
            "content_type": "abstract",
            "page_start": None,
            "page_end": None,
        }]
        citations = [{
            "citation_id": "demo-citation-1",
            "section_id": "section-demo-1",
            "paper_id": papers[0]["paper_id"],
            "claim_ids": [claim["claim_id"]],
            "evidence_ids": ["demo-evidence-1"],
            "display_number": 1,
        }]
        evidence = [{
            "evidence_id": "demo-evidence-1",
            "paper_id": papers[0]["paper_id"],
            "chunk_id": "demo-chunk-1",
            "claim_id": claim["claim_id"],
            "excerpt": evidence_excerpt,
            "content_type": "abstract",
            "page_start": None,
            "page_end": None,
            "support_type": "direct",
        }]

        await self._stage(task, cancel_event, ResearchStage.ORCHESTRATE, {"detail": _demo_text(locale, "plan_ready")})
        await self._append(task, EventType.PLAN_AVAILABLE, payload={"steps": plan})

        source_stats = _source_stats(papers, source_warning_active)
        await self._stage(
            task,
            cancel_event,
            ResearchStage.SEARCH,
            {
                "metrics": {"papers_discovered": len(papers)},
                "source_stats": source_stats,
            },
        )
        await self._append(task, EventType.PAPERS_DISCOVERED, payload={"count": len(papers)})
        if source_warning_active:
            await self._append(
                task,
                EventType.STAGE_WARNING,
                stage=ResearchStage.SEARCH,
                level=EventLevel.WARNING,
                payload={"message": _demo_text(locale, "source_warning"), "source": "crossref"},
            )

        await self._stage(task, cancel_event, ResearchStage.FILTER, {"metrics": {"papers_selected": len(selected)}})
        await self._append(task, EventType.PAPERS_SELECTED, payload={"count": len(selected)})

        await self._stage(task, cancel_event, ResearchStage.READ, {"metrics": {"papers_read": len(insights)}})
        for paper in selected:
            await self._append(task, EventType.PAPER_READ, stage=ResearchStage.READ, payload={"paper_id": paper["paper_id"]})

        await self._stage(task, cancel_event, ResearchStage.ANALYZE, {"metrics": {"agreements": 2, "gaps": 1}})
        analysis = {
            "agreements": [
                _demo_text(locale, "agreement_1"),
                _demo_text(locale, "agreement_2"),
            ],
            "contradictions": [],
            "gaps": [_demo_text(locale, "gap")],
        }
        await self._append(task, EventType.ANALYSIS_AVAILABLE, stage=ResearchStage.ANALYZE, payload={"keys": list(analysis)})

        await self._stage(task, cancel_event, ResearchStage.SYNTHESIZE, {"detail": "Draft report ready"})
        report = (
            f"# {task.title}\n\n"
            f"## {_demo_text(locale, 'findings_heading')}\n\n"
            f"{_demo_text(locale, 'report_finding')} "
            "[[CITE:demo-citation-1]] "
            f"{_demo_text(locale, 'report_warning') if source_warning_active else ''}\n\n"
            f"## {_demo_text(locale, 'limitations_heading')}\n\n"
            f"{_demo_text(locale, 'report_limitations')}"
        )
        await self._append(task, EventType.DRAFT_AVAILABLE, stage=ResearchStage.SYNTHESIZE, payload={"length": len(report)})
        await self._append(task, EventType.EVIDENCE_AVAILABLE, stage=ResearchStage.SYNTHESIZE, payload={"count": len(evidence)})

        await self._stage(task, cancel_event, ResearchStage.CRITIC, {"detail": "Critic review"})
        critique = {"attempt": 1, "score": 0.82, "approved": False, "summary": _demo_text(locale, "critique_first")}
        await self._append(task, EventType.CRITIQUE_COMPLETED, stage=ResearchStage.CRITIC, payload=critique)
        if self._critic_revisions:
            critique = {"attempt": 2, "score": 0.91, "approved": True, "summary": _demo_text(locale, "critique_final")}
            await self._append(task, EventType.CRITIQUE_COMPLETED, stage=ResearchStage.CRITIC, payload=critique)

        return {
            "user_query": task.query,
            "research_plan": plan,
            "raw_papers": papers,
            "selected_papers": selected,
            "paper_insights": insights,
            "paper_claims": [claim],
            "chunks": chunks,
            "citations": citations,
            "evidence": evidence,
            "structured_report": {"version": 1, "sections": [{"section_id": "section-demo-1", "heading": _demo_text(locale, "findings_heading"), "level": 2}]},
            "analysis_report": analysis,
            "critique": critique,
            "critique_history": [
                {"attempt": 1, "score": 0.82, "approved": False},
                critique,
            ],
            "final_answer": report,
            "errors": [],
            "warnings": [_demo_text(locale, "source_warning")] if source_warning_active else [],
        }

    async def _stage(
        self,
        task: TaskSnapshot,
        cancel_event: asyncio.Event,
        stage: ResearchStage,
        payload: Mapping[str, Any],
    ) -> None:
        await self._check_cancelled(cancel_event)
        started_at = time.perf_counter()
        await self._append(task, EventType.STAGE_STARTED, stage=stage, payload={})
        await self._delay(cancel_event)
        await self._append(task, EventType.STAGE_PROGRESS, stage=stage, payload=dict(payload))
        await self._append(
            task,
            EventType.STAGE_COMPLETED,
            stage=stage,
            payload={"duration_ms": max(0, int((time.perf_counter() - started_at) * 1000))},
        )

    async def _delay(self, cancel_event: asyncio.Event) -> None:
        if self._delay_seconds:
            await asyncio.sleep(self._delay_seconds)
        await self._check_cancelled(cancel_event)

    @staticmethod
    async def _check_cancelled(cancel_event: asyncio.Event) -> None:
        if cancel_event.is_set():
            raise asyncio.CancelledError

    async def _append(
        self,
        task: TaskSnapshot,
        event_type: EventType,
        *,
        stage: ResearchStage | None = None,
        level: EventLevel = EventLevel.INFO,
        payload: dict[str, Any] | None = None,
    ) -> None:
        append = getattr(self._event_recorder, "append")
        await append(task_id=task.id, event_type=event_type, stage=stage, level=level, payload=payload or {})


def _demo_text(locale: str, key: str, *, title: str = "") -> str:
    english = {
        "plan_question": "Frame the retrieval question",
        "plan_compare": "Compare multi-source evidence",
        "plan_synthesize": "Synthesize limitations and next steps",
        "insight": f"{title} reports stronger retrieval grounding.",
        "evidence": "Hybrid retrieval improves grounding.",
        "claim": "Hybrid retrieval improves grounding.",
        "plan_ready": "Plan ready",
        "source_warning": "Crossref demo source unavailable",
        "findings_heading": "Findings",
        "report_finding": "Hybrid retrieval improves grounding when metadata and semantic search are combined.",
        "report_warning": "The demo intentionally marks Crossref as unavailable so the partial-result path remains visible.",
        "limitations_heading": "Limitations",
        "report_limitations": "This deterministic report uses fixture papers and does not call external sources.",
        "critique_first": "Add a source-coverage caveat.",
        "critique_final": "Ready with source-coverage caveat.",
        "agreement_1": "Hybrid retrieval improves grounding.",
        "agreement_2": "Metadata quality affects ranking.",
        "gap": "Longitudinal evaluation remains limited.",
    }
    if locale == "zh-CN":
        return {
            **english,
            "plan_question": "明确检索问题",
            "plan_compare": "比较多来源证据",
            "plan_synthesize": "总结局限与后续方向",
            "insight": f"{title}报告了更强的检索依据。",
            "evidence": "混合检索能够提升论证依据。",
            "claim": "混合检索能够提升论证依据。",
            "plan_ready": "研究计划已准备好",
            "source_warning": "Crossref 演示来源不可用",
            "findings_heading": "研究发现",
            "report_finding": "结合元数据与语义检索时，混合检索能够提升论证依据。",
            "report_warning": "演示任务故意标记 Crossref 不可用，以展示部分结果路径。",
            "limitations_heading": "局限",
            "report_limitations": "此确定性报告使用固定论文样例，不会调用外部来源。",
            "critique_first": "补充来源覆盖范围说明。",
            "critique_final": "已补充来源覆盖范围说明，可以发布。",
            "agreement_1": "混合检索能够提升论证依据。",
            "agreement_2": "元数据质量会影响排序。",
            "gap": "长期评估仍然有限。",
        }.get(key, english[key])
    return english[key]


def _demo_papers(locale: str = "en") -> list[dict[str, Any]]:
    return [
        {
            "title": "Hybrid retrieval for scientific discovery",
            "authors": ["Ada Lovelace", "Grace Hopper"],
            "abstract": "Combines sparse and semantic retrieval for better grounding.",
            "source": "arxiv",
            "source_id": "arxiv:demo-001",
            "published_date": "2024",
            "citation_count": 42,
            "relevance_score": 4.8,
            "pdf_url": "https://example.com/demo-001.pdf",
        },
        {
            "title": "Full-text evaluation without an abstract",
            "authors": ["Katherine Johnson"],
            "abstract": "",
            "source": "semantic_scholar",
            "source_id": "semantic_scholar:demo-002",
            "published_date": "2023",
            "citation_count": 18,
            "relevance_score": 4.5,
            "pdf_url": "https://example.com/demo-002.pdf",
        },
        {
            "title": "Benchmarking evidence-grounded assistants",
            "authors": ["Alan Turing"],
            "abstract": "Defines evaluation tasks for evidence-grounded systems.",
            "source": "pubmed",
            "source_id": "pubmed:demo-003",
            "published_date": "2022",
            "citation_count": 11,
            "relevance_score": 4.1,
            "pdf_url": "",
        },
        {
            "title": "Unavailable metadata record",
            "authors": ["Demo Source"],
            "abstract": "",
            "source": "crossref",
            "source_id": "crossref:demo-004",
            "published_date": "2021",
            "citation_count": None,
            "relevance_score": None,
            "pdf_url": "",
            "full_text_status": "unavailable",
        },
        {
            "title": "Reranking methods for long-form research",
            "authors": ["Dorothy Vaughan"],
            "abstract": "Compares reranking strategies for long-form synthesis.",
            "source": "arxiv",
            "source_id": "arxiv:demo-005",
            "published_date": "2021",
            "citation_count": 9,
            "relevance_score": 3.9,
            "pdf_url": "https://example.com/demo-004.pdf",
        },
    ]


def _source_stats(papers: list[dict[str, Any]], source_warning_active: bool) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    for paper in papers:
        source = str(paper.get("source") or "unknown")
        bucket = stats.setdefault(source, {"papers": 0, "queries": 1, "errors": 0})
        bucket["papers"] += 1
    if source_warning_active:
        stats.setdefault("crossref", {"papers": 0, "queries": 1, "errors": 0})["errors"] = 1
    return stats
