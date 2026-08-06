import re
from typing import Any

from openai import AsyncOpenAI

from backend.config import settings
from backend.services.session_types import StoredSession


def _format_history(messages: list[dict], limit: int = 8) -> str:
    recent_messages = messages[-limit:]

    if not recent_messages:
        return "暂无之前的追问记录。"

    lines = []

    for message in recent_messages:
        role = message.get("role", "")
        content = message.get("content", "")

        if role == "user":
            speaker = "用户"
        elif role == "assistant":
            speaker = "助手"
        else:
            continue

        lines.append(f"{speaker}: {content}")

    return "\n\n".join(lines)


def _format_insights(
    insights: list[dict],
    limit: int = 8,
) -> str:
    if not insights:
        return "暂无论文证据。"

    blocks = []

    for insight in insights[:limit]:
        source = insight.get("source", "unknown")
        answer = insight.get("answer", "")

        # 避免单篇论文内容过长
        blocks.append(
            f"[Source {source}]\n"
            f"{answer[:1500]}"
        )

    return "\n\n".join(blocks)


def _extract_citations(answer: str) -> list[str]:
    """从 [Source xxx] 中提取引用来源。"""
    citations = re.findall(
        r"\[Source\s+([^\]]+)\]",
        answer,
        flags=re.IGNORECASE,
    )

    # 去重并保持原顺序
    return list(dict.fromkeys(citations))


async def answer_followup(
    question: str,
    session: StoredSession,
    messages: list[dict],
) -> dict[str, Any]:
    question = question.strip()

    if not question:
        raise ValueError("follow-up question cannot be empty")

    # 数据库中的研究结果
    research_result = session.get("result") or {}

    if not isinstance(research_result, dict):
        raise ValueError("stored research result is invalid")

    original_query = session.get("query", "")
    report = research_result.get("final_answer", "")
    analysis = research_result.get("analysis") or {}
    insights = research_result.get("paper_insights") or []

    history_text = _format_history(messages)
    insights_text = _format_insights(insights)

    client = AsyncOpenAI(
        api_key=settings.anthropic_api_key,
        base_url=settings.base_url,
        timeout=120.0,
        max_retries=2,
    )

    response = await client.chat.completions.create(
        model=settings.default_model,
        max_tokens=1500,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是学术研究报告的后续问答助手。"
                    "请根据已有研究报告、跨论文分析和论文证据回答用户追问。\n\n"
                    "要求：\n"
                    "1. 使用和用户相同的语言回答。\n"
                    "2. 优先解释现有报告中的结论。\n"
                    "3. 引用论文证据时使用 [Source 来源ID]。\n"
                    "4. 不得虚构当前上下文中不存在的论文、数据或结论。\n"
                    "5. 如果现有证据不足，请明确说明证据不足。\n"
                    "6. 除非用户明确要求，否则不要重新输出整篇综述。\n"
                    "7. 回答当前追问，不要偏离原始研究主题。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"原始研究问题：\n{original_query}\n\n"
                    f"当前研究报告：\n{report}\n\n"
                    f"跨论文分析：\n{analysis}\n\n"
                    f"论文证据：\n{insights_text}\n\n"
                    f"最近对话：\n{history_text}\n\n"
                    f"用户当前追问：\n{question}"
                ),
            },
        ],
    )

    answer = response.choices[0].message.content or ""
    answer = answer.strip()

    return {
        "answer": answer,
        "citations": _extract_citations(answer),
        "mode": "answer_from_context",
    }