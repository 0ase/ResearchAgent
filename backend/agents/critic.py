from __future__ import annotations

import json
import re

from openai import AsyncOpenAI

from backend.agents.state import ResearchState
from backend.config import settings
from backend.domain.reports import CritiqueResult, StructuredReport, review_report
from backend.services.run_context import context_from_state

MAX_CRITIQUE_ROUNDS = 2


async def critique_output(state: ResearchState) -> dict:
    """Review report quality with deterministic evidence checks plus model feedback."""
    draft = state.get("draft_sections", [])
    query = state.get("user_query", "")
    output_language = state.get("output_language", "en")
    context = context_from_state(state)
    if context:
        context.raise_if_cancelled()
    if not draft:
        return {"errors": ["no draft to critique"], "approved": True}

    current_round = state.get("critique_round", 0) + 1
    structured = state.get("structured_report")
    claims = state.get("paper_claims", [])
    paper_ids = {
        insight.get("paper_id") or insight.get("source")
        for insight in state.get("paper_insights", [])
        if insight.get("paper_id") or insight.get("source")
    }
    deterministic: CritiqueResult | None = None
    if structured:
        report = StructuredReport.model_validate(structured)
        deterministic = review_report(
            report,
            claim_ids={claim.get("claim_id") for claim in claims if claim.get("claim_id")},
            paper_ids=paper_ids,
            round_number=current_round,
        )

    review_text = draft[0].get("content", "")
    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.base_url,
        timeout=120.0,
        max_retries=2,
    )
    response = await client.chat.completions.create(
        model=settings.light_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a rigorous academic reviewer. Return ONLY JSON with "
                    "score, issues, approved and feedback. Check coverage, logical "
                    "consistency, citation accuracy and writing quality. Return "
                    f"feedback in {output_language}."
                ),
            },
            {
                "role": "user",
                "content": f"Original question: {query}\n\nLiterature review:\n{review_text}",
            },
        ],
    )
    model_critique = _parse_json(response.choices[0].message.content)
    if context:
        context.raise_if_cancelled()

    if deterministic is None:
        issues = model_critique.get("issues", [])
        score = float(model_critique.get("score", 5))
        approved = bool(model_critique.get("approved", score >= 7))
        critique = {
            "round": current_round,
            "score": score,
            "approved": approved or current_round >= MAX_CRITIQUE_ROUNDS,
            "issues": issues,
            "feedback": model_critique.get("feedback", ""),
        }
    else:
        merged_issues = [issue.model_dump() for issue in deterministic.issues]
        merged_issues.extend(
            {"code": "MODEL_REVIEW", "message": str(issue), "severity": "warning"}
            for issue in model_critique.get("issues", [])
            if str(issue) not in {item["message"] for item in merged_issues}
        )
        approved = deterministic.approved and bool(model_critique.get("approved", True))
        critique = deterministic.model_copy(
            update={
                "approved": approved or current_round >= MAX_CRITIQUE_ROUNDS,
                "issues": merged_issues,
                "feedback": deterministic.feedback or model_critique.get("feedback", ""),
            }
        ).model_dump()

    return {
        "critique": critique,
        "approved": critique.get("approved", True),
        "feedback": critique.get("feedback", ""),
        "critique_round": current_round,
        "critique_history": [
            {
                "round": current_round,
                "score": critique.get("score", 0),
                "issues": critique.get("issues", []),
                "evidence_review": critique.get("evidence_review", {}),
            }
        ],
    }


def _parse_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {"score": 5, "issues": ["could not parse critique"], "approved": True, "feedback": ""}
