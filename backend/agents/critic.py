from openai import AsyncOpenAI
from backend.agents.state import ResearchState
from backend.config import settings

async def critique_output(state: ResearchState) -> dict:
    """Evaluatte the synthesized review for quailty and completeness"""

    draft = state.get("draft_sections", [])
    query = state.get("user_query", "")

    if not draft:
        return {"error": ["no draft to critique"], "approved": True}
    
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
                    "relevance to the query, and writing quality. "
                    "Return ONLY valid JSON with: "
                    "score (1-10), issues (list of problems found), "
                    "approved (true if score >= 7 else false), "
                    "feedback (revision suggestions if not approved)."
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
    import re
    text = text.strip()
    try:
        import json
        return json.loads(text)
    except Exception:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            import json
            return json.loads(match.group(1))
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            import json
            return json.loads(match.group(0))
    return {"score": 5, "issues": ["could not parse critique"], "approved": True, "feedback": ""}