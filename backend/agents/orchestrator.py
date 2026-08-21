import json
import re
from openai import AsyncOpenAI
from backend.agents.state import ResearchState
from backend.config import settings

MIN_SUB_QUERIES = 3
MAX_SUB_QUERIES = 3


async def orchestrate(state: ResearchState) -> dict:
    """调 LLM 把研究问题拆解成多个子查询"""
    query = state["user_query"].strip()
    retrieval_focus = state.get("current_task", "").strip()

    system_prompt = """You are an academic research assistant.
Your task is to break down the ORIGINAL research question into exactly 3 specific sub-queries.
Each sub-query should be approached from a different perspective
or sub-field to facilitate precise search in the thesis database.
Never replace the original topic with a generic workflow instruction.
Only return a JSON array, no other content."""

    user_message = f"""Break down this research question into exactly 3 paper search sub-queries:
Original research question: "{query}"
Current retrieval focus: "{retrieval_focus or 'No additional focus'}"

Each query must preserve the original research topic. Cover different angles such as
recent advances, methods/comparisons, empirical evidence, and limitations.

Return ONLY a JSON array with exactly 3 strings:
["specific search query 1", "specific search query 2", "specific search query 3"]"""

    client = AsyncOpenAI(
        api_key=settings.anthropic_api_key,
        base_url=settings.base_url,
        timeout=60.0,
        max_retries=2,
    )
    response = await client.chat.completions.create(
        model=settings.light_model or settings.default_model,
        max_tokens=800,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    text = response.choices[0].message.content

    print(f"\n[Orchestrate] RAW LLM output ({len(text)} chars):")
    print(f"  {text[:500]}")

    # 容错解析：LLM 可能返回 ```json ... ``` 包裹的内容
    sub_queries = _ensure_sub_queries(_parse_json_array(text), query)

    print(f"\n[Orchestrate] Generated {len(sub_queries)} sub-queries:")
    for i, q in enumerate(sub_queries, 1):
        print(f"  {i}. {q[:120]}")

    plan = [{"sub_query": q, "status": "pending"} for q in sub_queries]

    return {"research_plan": plan}


def _ensure_sub_queries(sub_queries: list[str], user_query: str) -> list[str]:
    """保证检索计划始终包含 3 个与原问题相关且互不重复的查询。"""
    user_query = user_query.strip()
    if not user_query:
        raise ValueError("user query must not be blank")

    fallbacks = [
        user_query,
        f"{user_query} recent advances systematic review",
        f"{user_query} methods approaches comparative study",
        f"{user_query} empirical evaluation benchmarks results",
        f"{user_query} limitations challenges future directions",
    ]

    unique: list[str] = []
    seen: set[str] = set()
    for item in [*sub_queries, *fallbacks]:
        query = " ".join(str(item).split()).strip()
        key = query.casefold()
        if not query or key in seen:
            continue
        seen.add(key)
        unique.append(query)
        if len(unique) >= MAX_SUB_QUERIES:
            break

    if len(unique) < MIN_SUB_QUERIES:
        # user_query 为空只会在绕过 API schema 直接调用 Agent 时发生。
        base = user_query or "academic research topic"
        while len(unique) < MIN_SUB_QUERIES:
            unique.append(f"{base} research perspective {len(unique) + 1}")

    return unique


def _parse_json_array(text: str) -> list[str]:
    """从 LLM 返回的文本中提取 JSON 数组，兼容各种格式"""
    text = text.strip()

    # 尝试直接解析
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return [str(item) for item in result if str(item).strip()]
    except json.JSONDecodeError:
        pass

    # 尝试提取 ```json ... ``` 代码块
    match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1))
            if isinstance(result, list):
                return [str(item) for item in result if str(item).strip()]
        except json.JSONDecodeError:
            pass

    # 尝试找到第一个 [...]
    match = re.search(r"\[.*\]", text, re.DOTALL)  # 贪婪匹配拿完整数组
    if match:
        try:
            result = json.loads(match.group(0))
            if isinstance(result, list):
                return [str(item) for item in result if str(item).strip()]
        except json.JSONDecodeError:
            pass

    # 最后兜底：按行拆分
    lines = [l.strip().strip('"').strip("'").lstrip("0123456789.- ").strip('"').strip("'") for l in text.split("\n") if l.strip()]
    lines = [l for l in lines if len(l) > 5]
    if lines:
        return lines[:5]

    # 彻底失败：返回原始查询
    return [text[:200]]
