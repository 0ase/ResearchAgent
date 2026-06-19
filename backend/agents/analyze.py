from openai import AsyncOpenAI
from backend.agents.state import ResearchState
from backend.config import settings

async def analyze_papers(state: ResearchState) -> dict:
    """Cross-paper comparative analysis: identifying commonalities, contradictions, method comparisons, and research gaps"""

    insights = state.get("paper_insights", [])
    query = state.get("user_query", "")

    if not insights:
        return {"error": ["no insights to analyze"]}

    all_insights = "\n\n".join([
        f"### Paper {i+1}\n{insight.get('answer', '')}"
        for i, insight in enumerate(insights)
    ])

    client = AsyncOpenAI(
        api_key=settings.anthropic_api_key,
        base_url=settings.base_url,
    )
    response = await client.chat.completions.create(
        model=settings.default_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a research meta-analyst. Analyze the provided paper "
                    "summaries and identify: agreements, contradictions, "
                    "methodological differences, and research gaps. "
                    "Return ONLY valid JSON with these keys: "
                    "agreements (list), contradictions (list), "
                    "methods (dict: method_name -> paper_index), gaps (list)."
                ),
            },
            {
                "role": "user",
                "content": f"Research question: {query}\n\nPaper summaries:\n{all_insights}\n\n, Return JSON analysis"
            }
        ]
    )

    import json
    text = response.choices[0].message.content
    analysis  =_parse_json(text)

    return {"analysis_report": analysis}

def _parse_json(text: str) -> dict:
    """parse the Json that LLM return"""
    import re
    text = text.strip()
    try:
        return __import__("json").loads(text)
    except Exception:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            return __import__("json").loads(match.group(1))
        match = re.search(r"\{.*?\}", text, re.DOTALL)
        if match:
            return __import__("json").loads(match.group(0))
    return {"agreements": [], "contradictions": [], "methods": {}, "gaps": []}