import json
import re
from openai import AsyncOpenAI
from backend.agents.state import ResearchState
from backend.config import settings
from backend.services.run_context import context_from_state


async def orchestrate(state: ResearchState) -> dict:
    """调 LLM 把研究问题拆解成多个子查询"""
    query = state["user_query"]
    output_language = state.get("output_language", "en")
    context = context_from_state(state)
    if context:
        context.raise_if_cancelled()

    system_prompt = """You are an academic research assistant.
Break the research question into 3-5 specific search angles.
Return ONLY a JSON array of objects. Each object must have:
- display_query: a concise query in the user's visible language
- retrieval_query: a concise English academic database query
Keep paper metadata and identifiers untranslated; translate only the search intent."""

    user_message = f"""Break down this research question into 3-5 paper search angles:
    "{query}"

    Return ONLY a JSON array of objects. The user's visible research language is {output_language}:
    [{{"display_query":"...", "retrieval_query":"English academic query"}}]"""

    client = AsyncOpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.base_url,
        timeout=60.0,
        max_retries=2,
    )
    response = await client.chat.completions.create(
        model=settings.default_model,
        max_tokens=800,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    text = response.choices[0].message.content
    if context:
        context.raise_if_cancelled()

    print(f"\n[Orchestrate] RAW LLM output ({len(text)} chars):")
    print(f"  {text[:500]}")

    query_plan = _normalize_query_plan(
        _parse_json_value(text),
        output_language=output_language,
    )

    if output_language == "zh-CN" and any(
        not item["retrieval_query"] for item in query_plan
    ):
        completion_response = await client.chat.completions.create(
            model=settings.light_model,
            max_tokens=600,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Translate research search intents into concise English academic "
                        "database queries. Return ONLY a JSON array of strings."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        [item["display_query"] for item in query_plan],
                        ensure_ascii=False,
                    ),
                },
            ],
        )
        completions = _parse_json_value(completion_response.choices[0].message.content)
        for item, retrieval_query in zip(
            query_plan,
            _string_values(completions),
        ):
            if not item["retrieval_query"] and _looks_like_english_query(retrieval_query):
                item["retrieval_query"] = retrieval_query.strip()[:200]

    warnings = []
    if any(not item["retrieval_query"] for item in query_plan):
        warnings.append("QUERY_TRANSLATION_INCOMPLETE")

    print(f"\n[Orchestrate] Generated {len(query_plan)} sub-queries:")
    for i, item in enumerate(query_plan, 1):
        print(f"  {i}. {item['retrieval_query'] or item['display_query'][:120]}")

    plan = [
        {
            "sub_query": item["display_query"],
            "display_query": item["display_query"],
            "retrieval_query": item["retrieval_query"],
            "status": "pending",
        }
        for item in query_plan
    ]

    return {
        "research_plan": plan,
        "search_round": 1,
        "warnings": warnings,
    }


def _parse_json_value(text: str):
    """Extract a JSON value from a model response."""
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*([\[{].*?[\]}])\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return []


def _normalize_query_plan(value, *, output_language: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    normalized = []
    for item in value[:5]:
        if isinstance(item, dict):
            display_query = str(
                item.get("display_query") or item.get("sub_query") or ""
            ).strip()
            retrieval_query = str(item.get("retrieval_query") or "").strip()
            if not retrieval_query and output_language == "en":
                retrieval_query = display_query
        elif isinstance(item, str):
            display_query = item.strip()
            retrieval_query = (
                display_query
                if output_language == "en" or _looks_like_english_query(display_query)
                else ""
            )
        else:
            continue

        if display_query:
            normalized.append(
                {
                    "display_query": display_query[:200],
                    "retrieval_query": retrieval_query[:200],
                }
            )
    return normalized


def _string_values(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _looks_like_english_query(value: str) -> bool:
    return any("a" <= char.lower() <= "z" for char in value)
