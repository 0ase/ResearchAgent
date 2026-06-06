import json
import re
from openai import AsyncOpenAI
from backend.agents.state import ResearchState
from backend.config import settings


async def orchestrate(state: ResearchState) -> dict:
    """调 LLM 把研究问题拆解成多个子查询"""
    query = state["user_query"]

    system_prompt = """You are an academic research assistant.
Your task is to break down the user's research question into 3-5 specific sub-queries.
Each sub-query should be approached from a different perspective
or sub-field to facilitate precise search in the thesis database.
Only return a JSON array, no other content."""

    user_message = f"""Break down this research question into 3-5 paper search sub-queries:
    "{query}"

    Return ONLY a JSON array:
    ["sub-query 1: specific angle", "sub-query 2: specific angle", ...]"""

    client = AsyncOpenAI(api_key=settings.anthropic_api_key, base_url=settings.base_url)
    response = await client.chat.completions.create(
        model=settings.default_model,
        max_tokens=500,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    text = response.choices[0].message.content

    # 容错解析：LLM 可能返回 ```json ... ``` 包裹的内容
    sub_queries = _parse_json_array(text)

    plan = [{"sub_query": q, "status": "pending"} for q in sub_queries]

    return {
        "research_plan": plan,
        "search_round": 1,
    }


def _parse_json_array(text: str) -> list[str]:
    """从 LLM 返回的文本中提取 JSON 数组，兼容各种格式"""
    text = text.strip()

    # 尝试直接解析
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # 尝试提取 ```json ... ``` 代码块
    match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # 尝试找到第一个 [...]
    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(0))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # 最后兜底：按行拆分
    lines = [l.strip().strip('"').strip("'").lstrip("0123456789.- ").strip('"').strip("'") for l in text.split("\n") if l.strip()]
    lines = [l for l in lines if len(l) > 5]
    if lines:
        return lines[:5]

    # 彻底失败：返回原始查询
    return [text[:200]]
