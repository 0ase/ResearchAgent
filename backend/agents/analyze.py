from __future__ import annotations

import json
import re

from openai import AsyncOpenAI

from backend.agents.state import ResearchState
from backend.config import settings
from backend.services.structured_output import (
    AnalysisFinding,
    AnalysisOutput,
    parse_model_output,
    validate_analysis_findings,
)
from backend.services.run_context import context_from_state


async def analyze_papers(state: ResearchState) -> dict:
    """Compare stable Paper Claims and return compatible + structured findings."""
    insights = state.get("paper_insights", [])
    query = state.get("user_query", "")
    output_language = state.get("output_language", "en")
    context = context_from_state(state)

    if not insights:
        return {"errors": ["no insights to analyze"], "analysis_findings": []}

    all_insights = "\n\n".join(
        [
            f"### Paper ID: {insight.get('paper_id') or insight.get('source', 'unknown')}\n"
            f"Summary: {insight.get('answer', '')}\n"
            f"Claims: {json.dumps(insight.get('claims', []), ensure_ascii=False)}"
            for insight in insights
        ]
    )

    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.base_url,
    )
    if context:
        context.raise_if_cancelled()
    response = await client.chat.completions.create(
        model=settings.default_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a research meta-analyst. Compare the supplied Paper Claims. "
                    "Return ONLY valid JSON with a findings list. Each finding must have "
                    "finding_id, kind, statement, claim_ids and paper_ids. Use at least "
                    "two existing claim_ids for an agreement. A gap is an analysis "
                    "inference. Never invent IDs. Write finding statements in "
                    f"{output_language}."
                ),
            },
            {
                "role": "user",
                "content": f"Research question: {query}\n\n{all_insights}\n\nReturn JSON.",
            },
        ],
    )

    text = response.choices[0].message.content
    if context:
        context.raise_if_cancelled()
    parsed = parse_model_output(text, AnalysisOutput)
    claim_ids = {
        claim.get("claim_id")
        for insight in insights
        for claim in insight.get("claims", [])
        if claim.get("claim_id")
    }
    paper_ids = {
        insight.get("paper_id") or insight.get("source")
        for insight in insights
        if insight.get("paper_id") or insight.get("source")
    }

    if parsed is None:
        return {"analysis_report": _parse_json(text), "analysis_findings": []}

    findings = validate_analysis_findings(
        parsed.findings,
        claim_ids=claim_ids,
        paper_ids=paper_ids,
    )
    return {
        "analysis_report": _legacy_analysis_report(findings),
        "analysis_findings": [finding.model_dump() for finding in findings],
    }


def _legacy_analysis_report(findings: list[AnalysisFinding]) -> dict:
    return {
        "agreements": [
            finding.statement
            for finding in findings
            if finding.kind == "agreement" and finding.valid
        ],
        "contradictions": [
            finding.statement
            for finding in findings
            if finding.kind == "contradiction" and finding.valid
        ],
        "methods": {
            finding.finding_id: finding.statement
            for finding in findings
            if finding.kind == "method" and finding.valid
        },
        "gaps": [finding.statement for finding in findings if finding.kind == "gap"],
    }


def _parse_json(text: str) -> dict:
    """Backward-compatible tolerant parser for legacy model responses."""
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
    return {"agreements": [], "contradictions": [], "methods": {}, "gaps": []}
