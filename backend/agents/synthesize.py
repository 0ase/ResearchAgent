from __future__ import annotations

from openai import AsyncOpenAI

from backend.agents.state import ResearchState
from backend.config import settings
from backend.domain.reports import (
    CitationDraft,
    ReportDraft,
    build_structured_report,
    citation_id_for_claim,
    next_draft_version,
    report_has_substantive_text,
)
from backend.services.structured_output import parse_model_output
from backend.services.run_context import context_from_state


async def synthesize_review(state: ResearchState) -> dict:
    """Write a Markdown-compatible report plus a validated structured snapshot."""
    insights = state.get("paper_insights", [])
    analysis = state.get("analysis_report", {})
    findings = state.get("analysis_findings", [])
    claims = state.get("paper_claims", []) or [
        claim
        for insight in insights
        for claim in insight.get("claims", [])
    ]
    query = state.get("user_query", "")
    output_language = state.get("output_language", "en")
    context = context_from_state(state)

    if not insights:
        return {"errors": ["no insights to synthesize"]}

    context_parts = []
    for insight in insights:
        context_parts.append(
            f"### Paper ID: {insight.get('paper_id') or insight.get('source', 'unknown')}\n"
            f"Summary: {insight.get('answer', '')}\n"
            f"Claims: {insight.get('claims', [])}"
        )
    paper_summaries = "\n\n".join(context_parts)
    analysis_text = str({"report": analysis, "findings": findings}) if analysis or findings else "No cross-paper analysis available."
    citation_catalog = [
        {
            "citation_id": citation_id_for_claim(claim["claim_id"]),
            "claim_ids": [claim["claim_id"]],
            "paper_id": claim.get("paper_id", ""),
            "chunk_ids": claim.get("chunk_ids", []),
        }
        for claim in claims
        if claim.get("claim_id")
    ]

    feedback = state.get("feedback", "")
    revision_note = (
        f"\nPrevious draft feedback to address:\n{feedback}\n"
        if feedback
        else ""
    )
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.base_url,
        timeout=180.0,
        max_retries=2,
    )
    response = await client.chat.completions.create(
        model=settings.default_model,
        max_tokens=4000,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an academic literature review writer. Return ONLY JSON "
                    "with markdown and citations. Use the supplied citation_id values "
                    "and cite them in Markdown as [[CITE:citation_id]]. Do not invent "
                    "paper, claim, chunk, or citation IDs. Write the report in "
                    f"{output_language}."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Research question: {query}\n\n"
                    f"Paper summaries and claims:\n{paper_summaries}\n\n"
                    f"Cross-paper analysis:\n{analysis_text}\n\n"
                    f"Citation catalogue:\n{citation_catalog}\n"
                    f"{revision_note}\nWrite the report."
                ),
            },
        ],
    )

    raw_text = response.choices[0].message.content.strip()
    if context:
        context.raise_if_cancelled()
    parsed = parse_model_output(raw_text, ReportDraft)
    markdown = parsed.markdown if parsed is not None else raw_text
    if not report_has_substantive_text(markdown):
        markdown = _fallback_report(
            query=query,
            output_language=output_language,
            insights=insights,
            findings=findings,
            claims=claims,
            citation_catalog=citation_catalog,
        )
    citations = (
        parsed.citations
        if parsed is not None and parsed.citations
        else [CitationDraft(**citation) for citation in citation_catalog]
    )
    if citation_catalog and not _contains_citation_token(markdown):
        markdown = (
            markdown.rstrip()
            + "\n\n"
            + " ".join(f"[[CITE:{citation['citation_id']}]]" for citation in citation_catalog)
        )
    version = next_draft_version(
        state.get("structured_report") and state.get("structured_report")
    )
    report = build_structured_report(
        markdown,
        citations=citations,
        claim_ids={claim.get("claim_id") for claim in claims if claim.get("claim_id")},
        chunk_ids={
            chunk_id
            for claim in claims
            for chunk_id in claim.get("chunk_ids", [])
        },
        version=version,
    )
    return {
        "structured_report": report.model_dump(),
        "draft_version": version,
        "draft_sections": [
            {
                "section_id": section.section_id,
                "title": section.heading,
                "level": section.level,
                "content": section.markdown,
                "citation_ids": section.citation_ids,
            }
            for section in report.sections
        ],
        "final_answer": markdown,
    }


def _contains_citation_token(markdown: str) -> bool:
    return "[[CITE:" in markdown


def _fallback_report(
    *,
    query: str,
    output_language: str,
    insights: list[dict],
    findings: list[dict],
    claims: list[dict],
    citation_catalog: list[dict],
) -> str:
    """Build a readable report when a provider returns citation-only output."""
    is_zh = output_language.lower().startswith("zh")
    lines = [
        "# 研究综合报告" if is_zh else "# Research synthesis report",
        "",
        ("## 研究问题" if is_zh else "## Research question"),
        query.strip() or ("本次研究围绕已检索论文进行综合。" if is_zh else "This report synthesizes the retrieved papers."),
        "",
        ("## 主要发现" if is_zh else "## Key findings"),
    ]
    claim_by_id = {
        str(claim.get("claim_id")): claim
        for claim in claims
        if claim.get("claim_id")
    }
    added = 0
    for citation in citation_catalog:
        citation_claim_ids = citation.get("claim_ids") or []
        claim = (
            claim_by_id.get(str(citation_claim_ids[0]))
            if citation_claim_ids
            else None
        )
        statement = str((claim or {}).get("statement") or "").strip()
        if not statement:
            continue
        lines.append(
            f"- {statement} [[CITE:{citation['citation_id']}]]"
        )
        added += 1
    if not added:
        for insight in insights:
            answer = str(insight.get("answer") or "").strip()
            if answer:
                lines.append(f"- {answer}")
    if not any(line.startswith("-") for line in lines):
        lines.append(
            "- 已完成论文检索与证据整理，但模型未返回可引用的文字结论。"
            if is_zh
            else "- The papers were retrieved and evidence was collected, but no prose conclusion was returned."
        )
    lines.extend(
        [
            "",
            ("## 证据范围与局限" if is_zh else "## Evidence scope and limitations"),
            (
                f"本报告基于 {len(insights)} 篇已读取论文及其可追踪分块；部分来源或全文可能不可用。"
                if is_zh
                else f"This report is based on {len(insights)} readable papers and traceable chunks; some sources or full text may be unavailable."
            ),
        ]
    )
    return "\n".join(lines)
