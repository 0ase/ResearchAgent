import json
import re

from openai import AsyncOpenAI
from backend.services.provider_retry import chat_completion

from backend.agents.report_quality import find_report_completeness_issues
from backend.agents.state import ResearchState
from backend.config import settings
from backend.domain.reports import CitationDraft, build_structured_report, citation_id_for_claim, next_draft_version
from backend.services.run_context import context_from_state
from backend.domain.reports import report_has_substantive_text
from backend.agents.report_fallback import _fallback_report


def _format_authors(authors: object) -> str:
    if not isinstance(authors, list):
        return str(authors or "Unknown")
    names = []
    for author in authors[:8]:
        if isinstance(author, dict):
            names.append(str(author.get("name") or author.get("author") or ""))
        else:
            names.append(str(author))
    return ", ".join(name for name in names if name) or "Unknown"


def _length_instruction(query: str, output_language: str | None = None) -> str:
    if output_language == "zh-CN" or (output_language is None and re.search(r"[\u3400-\u9fff]", query)):
        return (
            f"正文目标为 {settings.writer_min_characters}–8000 个中文字符（参考文献不计入），"
            "在证据足够时应接近目标上限。"
        )
    return (
        "Target 2,500–4,000 words excluding references, while prioritizing "
        "evidence density over repetition."
    )


def _build_writer_messages(state: ResearchState) -> list[dict]:
    insights = state.get("paper_insights", [])
    analysis = state.get("analysis_report", {})
    query = state.get("user_query", "")
    objective = state.get("current_task", "")
    selected_by_id = {
        str(paper.get("paper_id") or paper.get("source_id")): paper
        for paper in state.get("selected_papers", [])
        if paper.get("source_id")
    }

    evidence_blocks = []
    for i, insight in enumerate(insights, 1):
        source_id = str(insight.get("source") or f"paper_{i}")
        paper = selected_by_id.get(source_id, {})
        title = paper.get("title") or "Title unavailable"
        evidence_blocks.append(
            f"[Source {source_id}]\n"
            f"Title: {title}\n"
            f"Authors: {_format_authors(paper.get('authors'))}\n"
            f"Published: {paper.get('published_date') or 'Unknown'}\n"
            f"DOI: {paper.get('doi') or 'Unknown'}\n"
            f"Evidence: {insight.get('answer', '')}"
        )
    evidence_text = "\n\n".join(evidence_blocks)

    analysis_text = (
        json.dumps(analysis, ensure_ascii=False, indent=2)
        if analysis
        else "No cross-paper analysis available."
    )

    feedback = state.get("feedback", "")
    revision_note = ""
    if feedback:
        revision_note = (
            "\n\nIMPORTANT REVISION REQUIREMENTS FROM THE CRITIC:\n"
            f"{feedback}\n"
            "Address every requirement explicitly while returning a complete "
            "replacement report."
        )

    return [
        {
            "role": "system",
            "content": (
                "You are a senior academic literature review writer. Produce a "
                "substantive thematic synthesis that directly answers the research "
                "question, not an annotated bibliography or a list of paper "
                "summaries. Organize the body by concepts, method families, findings, "
                "agreements, contradictions, and evidence strength. Do NOT create one "
                "heading or paragraph per paper, and do NOT use headings such as "
                "'Paper 1', 'Paper 2', or source IDs. Combine evidence from multiple "
                "sources in each analytical paragraph whenever possible.\n\n"
                "Return one complete markdown report with these parts: title; abstract "
                "or executive summary; introduction and scope; evidence base and "
                "methodological landscape; 3–5 thematic comparative-analysis "
                "subsections; agreements, contradictions and limitations; research "
                "gaps and future directions; conclusion; and references. A concise "
                "markdown comparison table is welcome when it improves clarity, but "
                "tables do not replace analysis.\n\n"
                "Cite factual claims inline ONLY as [[CITE:citation_id]], using the supplied catalogue. Never invent a source, "
                "result, author, date, or bibliographic field. Include in References "
                "only sources cited in the body and use the metadata supplied below. "
                "Discuss evidence quality and uncertainty where the excerpts are "
                f"insufficient. Write in {state.get('output_language', 'the language of the question')}. "
                "Do not end early: finish every required section and the References. "
                "Add depth through comparison and reasoning, not filler or repeated "
                "paper descriptions."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Research question: {query}\n\n"
                f"Current writing objective: {objective}\n\n"
                f"Length requirement: {_length_instruction(query, state.get('output_language'))}\n\n"
                "The following material is evidence, not an outline. Select, compare, "
                "and combine the evidence needed to answer the question. Make the "
                "relationship among methods, findings, disagreements, limitations, "
                "and open problems explicit.\n\n"
                f"Source evidence:\n{evidence_text}\n\n"
                f"Cross-paper analysis:\n{analysis_text}\n"
                f"Citation catalogue: {json.dumps(_citation_catalog(state), ensure_ascii=False)}"
                f"{revision_note}\n\n"
                "Write the complete integrated literature review in markdown now."
            ),
        },
    ]


def _completion_text_and_reason(response) -> tuple[str, str]:
    choice = response.choices[0]
    return (
        (choice.message.content or "").strip(),
        str(getattr(choice, "finish_reason", "") or ""),
    )


def _join_continuation(report: str, continuation: str) -> str:
    report = report.rstrip()
    continuation = continuation.lstrip()
    if not report:
        return continuation
    if report.endswith(("。", "！", "？", ".", "!", "?", ";", "；", ":", "：")):
        return f"{report}\n\n{continuation}"
    return f"{report}{continuation}"


async def _continue_report(
    client: AsyncOpenAI,
    state: ResearchState,
    report: str,
) -> tuple[str, str]:
    messages = _build_writer_messages(state)
    messages.extend([
        {"role": "assistant", "content": report},
        {
            "role": "user",
            "content": (
                "The response was cut off by the output limit. Continue from the "
                "exact final character without repeating any existing text. Complete "
                "the current sentence first, then finish all remaining required "
                "sections, including conclusion and References. Return ONLY the "
                "continuation, in the same language and citation style."
            ),
        },
    ])
    response = await chat_completion(client,
        model=settings.default_model,
        max_tokens=settings.writer_continuation_tokens,
        messages=messages,
    )
    return _completion_text_and_reason(response)


async def _rewrite_incomplete_report(
    client: AsyncOpenAI,
    state: ResearchState,
    report: str,
    issues: list[str],
) -> tuple[str, str]:
    messages = _build_writer_messages(state)
    messages.extend([
        {"role": "assistant", "content": report},
        {
            "role": "user",
            "content": (
                "The draft above is incomplete. Problems detected:\n- "
                + "\n- ".join(issues)
                + "\nRewrite and return the ENTIRE improved report, not a patch or "
                "commentary. Preserve valid citations, expand the comparative "
                "reasoning, meet the requested length, and complete every required "
                "section through References."
            ),
        },
    ])
    response = await chat_completion(client,
        model=settings.default_model,
        max_tokens=settings.writer_max_tokens,
        messages=messages,
    )
    return _completion_text_and_reason(response)


async def synthesize_review(state: ResearchState) -> dict:
    """Write a complete thematic review and repair abnormal short/truncated output."""
    context = context_from_state(state)
    if context:
        context.raise_if_cancelled()
    if not state.get("paper_insights"):
        return {"errors": ["no insights to synthesize"]}

    client = AsyncOpenAI(
        api_key=settings.anthropic_api_key,
        base_url=settings.base_url,
        timeout=300.0,
        max_retries=0,
    )
    response = await chat_completion(client,
        model=settings.default_model,
        max_tokens=settings.writer_max_tokens,
        messages=_build_writer_messages(state),
    )
    review, finish_reason = _completion_text_and_reason(response)
    attempts = 1

    # Most requests use one call. Extra calls happen only when deterministic checks
    # detect truncation or a materially incomplete report.
    while review and attempts < 3:
        if context:
            context.raise_if_cancelled()
        issues = find_report_completeness_issues(review, finish_reason)
        if not issues:
            break

        attempts += 1
        if finish_reason == "length":
            continuation, finish_reason = await _continue_report(client, state, review)
            if not continuation:
                break
            review = _join_continuation(review, continuation)
        else:
            candidate, candidate_reason = await _rewrite_incomplete_report(
                client,
                state,
                review,
                issues,
            )
            if not candidate:
                break
            old_score = (len(issues), -len(review))
            candidate_issues = find_report_completeness_issues(
                candidate,
                candidate_reason,
            )
            candidate_score = (len(candidate_issues), -len(candidate))
            if candidate_score >= old_score:
                break
            review, finish_reason = candidate, candidate_reason

    if not report_has_substantive_text(review):
        review = _fallback_report(query=state.get("user_query", ""), output_language=state.get("output_language", "en"),
            insights=state.get("paper_insights", []), findings=state.get("analysis_findings", []),
            claims=state.get("paper_claims", []), citation_catalog=_citation_catalog(state))

    remaining_issues = find_report_completeness_issues(review, finish_reason)
    context = context_from_state(state)
    if context:
        context.raise_if_cancelled()
    catalog = [CitationDraft(**item) for item in _citation_catalog(state)]
    report = build_structured_report(review, citations=catalog,
        claim_ids={cid for c in catalog for cid in c.claim_ids},
        chunk_ids={cid for c in catalog for cid in c.chunk_ids},
        version=next_draft_version(state.get("structured_report")))
    return {
        "structured_report": report.model_dump(),
        "draft_version": report.version,
        "draft_sections": [{"title": "Literature Review", "content": review}],
        "final_answer": review,
        "critique": None,
        "approved": False,
        "feedback": None,
        "writer_finish_reason": finish_reason,
        "writer_generation_attempts": attempts,
        "writer_incomplete": bool(remaining_issues),
    }


def _citation_catalog(state):
    claims = state.get("paper_claims", []) or [c for i in state.get("paper_insights", []) for c in i.get("claims", [])]
    return [{"citation_id": citation_id_for_claim(c["claim_id"]), "claim_ids": [c["claim_id"]],
             "paper_id": c.get("paper_id", ""), "chunk_ids": c.get("chunk_ids", [])}
            for c in claims if c.get("claim_id")]
