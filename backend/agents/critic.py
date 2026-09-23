import json
import re

from openai import AsyncOpenAI, OpenAIError
from backend.services.provider_retry import chat_completion
from backend.agents.report_quality import find_report_completeness_issues
from backend.agents.state import ResearchState
from backend.config import settings
from backend.domain.reports import StructuredReport, review_report

async def critique_output(state: ResearchState) -> dict:
    """Evaluatte the synthesized review for quailty and completeness"""

    draft = state.get("draft_sections", [])
    query = state.get("user_query", "")

    if not draft:
        return {
            "errors": ["no draft to critique"],
            "critique": {
                "score": 0,
                "approved": False,
                "issue_type": "writing_quality",
                "issues": ["no draft to critique"],
                "feedback": "Generate a report draft before critique.",
            },
            "approved": False,
        }
    
    review_text = draft[0].get("content", "")
    
    try:
        client = AsyncOpenAI(
            api_key=settings.anthropic_api_key,
            base_url=settings.base_url,
            timeout=120.0,
            max_retries=0,
        )
        response = await chat_completion(client,
            model=settings.light_model or settings.default_model,
            max_tokens=1200,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a rigorous academic reviewer. Evaluate the literature "
                        "review against the original research question. Check for: "
                        "coverage gaps, logical consistency, citation accuracy, "
                        "relevance to the query, writing quality, report completeness, "
                        "and whether the discussion is sufficiently detailed rather "
                        "than a paper-by-paper list.\n"
                        "issues contains only blocking problems; put non-blocking observations in feedback. "
                        "Non-empty issues requires approved=false. approved=true requires issue_type=none and issues=[]. "
                        "Missing explicitly requested paper types, independent baselines, evaluation conditions or evidence coverage "
                        "must use insufficient_evidence or analysis_gap and cannot be approved. "
                        "Return ONLY valid JSON with the following structure:\n"
                        '{\n'
                        '  "score": 1-10,\n'
                        '  "approved": true or false,\n'
                        '  "issue_type": "none" | "insufficient_evidence" | "analysis_gap" | "citation_error" | "writing_quality",\n'
                        '  "issues": [],\n'
                        '  "feedback": ""\n'
                        '}\n'
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Original question: {query}\n\n"
                        f"Literature review:\n{review_text}\n\n"
                        "Evaluate this review. Return JSON."
                    ),
                },
            ],
        )

        text = response.choices[0].message.content
    except (OpenAIError, TimeoutError):
        # Keep a usable draft when review cannot run; never label it approved.
        number = state.get("critique_round", 0) + 1
        return {"critique": {"approved": False, "provider_unavailable": True,
                              "issues": ["CRITIQUE_NOT_APPROVED"], "score": 0},
                "approved": False, "critique_round": number,
                "critique_history": [{"round": number, "score": 0, "issues": ["CRITIQUE_NOT_APPROVED"]}],
                "warnings": ["CRITIQUE_NOT_APPROVED"]}

    critique = _parse_json(text)
    score = critique.get("score", 0)
    try:
        numeric_score = float(score)
    except (TypeError, ValueError):
        numeric_score = 0
    completeness_issues = find_report_completeness_issues(
        review_text,
        state.get("writer_finish_reason"),
    )
    evidence_review = None
    if state.get("structured_report"):
        evidence_review = review_report(
            StructuredReport.model_validate(state["structured_report"]),
            claim_ids={c["claim_id"] for c in state.get("paper_claims", []) if c.get("claim_id")},
            paper_ids={i.get("paper_id") or i.get("source") for i in state.get("paper_insights", [])},
            round_number=state.get("critique_round", 0) + 1,
        )
        completeness_issues.extend(issue.message for issue in evidence_review.issues)
        critique["evidence_review"] = evidence_review.evidence_review.model_dump()
        if not evidence_review.approved:
            critique["issue_type"] = "citation_error"
    approved = (
        critique.get("approved") is True
        and numeric_score >= 7
        and critique.get("issue_type") == "none"
        and critique.get("issues") == []
        and evidence_review is not None
        and evidence_review.approved
        and not completeness_issues
    )
    critique["approved"] = approved
    if completeness_issues:
        issues = list(critique.get("issues") or [])
        for issue in completeness_issues:
            if issue not in issues:
                issues.append(issue)
        critique["issues"] = issues
        if critique.get("issue_type") in {None, "", "none"}:
            critique["issue_type"] = "writing_quality"
        completeness_feedback = (
            "报告未满足完整性硬性要求："
            + "；".join(completeness_issues)
            + "。请返回一份完整扩展后的报告，不能只提供补丁。"
        )
        existing_feedback = str(critique.get("feedback") or "").strip()
        critique["feedback"] = "\n".join(
            item for item in (existing_feedback, completeness_feedback) if item
        )
    elif approved:
        critique["issue_type"] = "none"
        critique["feedback"] = ""

    return {
        "critique": critique,
        "approved": approved,
        "feedback": critique.get("feedback", ""),
        "critique_round": state.get("critique_round", 0) + 1,
        "critique_history": [{                              
            "round": state.get("critique_round", 0) + 1,
            "score": critique.get("score", 0),
            "issues": critique.get("issues", []),
        }],
    }



def _parse_json(text: str) -> dict:
    """Tolerant JSON parser"""
    text = text.strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    for pattern in (
        r"```(?:json)?\s*(\{.*?\})\s*```",
        r"\{.*\}",
    ):
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            continue
        candidate = match.group(1) if match.lastindex else match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    return {
        "score": 5,
        "issues": ["could not parse critique"],
        "approved": False,
        "issue_type": "writing_quality",
        "feedback": "Critique output was invalid; review the draft again.",
    }
