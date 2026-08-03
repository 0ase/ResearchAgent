import json
import re

from openai import AsyncOpenAI
from backend.agents.state import ResearchState
from backend.config import settings

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
    
    client = AsyncOpenAI(
        api_key=settings.anthropic_api_key,
        base_url=settings.base_url,
        timeout=120.0,
        max_retries=2,
    )
    response = await client.chat.completions.create(
        model=settings.default_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a rigorous academic reviewer. Evaluate the literature "
                    "review against the original research question. Check for: "
                    "coverage gaps, logical consistency, citation accuracy, "
                    "relevance to the query, and writing quality.\n"
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
    critique = _parse_json(text)

    return {
        "critique": critique,
        "approved": critique.get("approved", True),
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
