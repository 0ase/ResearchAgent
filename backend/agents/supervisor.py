import json
import re
from typing import Literal

from openai import AsyncOpenAI
from langgraph.types import Command

from backend.agents.contracts import SupervisorDecision
from backend.agents.policy import validate_decision
from backend.agents.state import ResearchState
from backend.config import settings

ROUTES = Literal[
    "retrieval",
    "analysis",
    "writer",
    "critic",
    "finish",
]


def summarize_state(state: ResearchState) -> dict:
    critique = state.get("critique") or {}

    return {
        "user_query": state.get("user_query", ""),
        "last_task": state.get("current_task", ""),
        "papers_found": len(state.get("raw_papers", [])),
        "papers_selected": len(state.get("selected_papers", [])),
        "papers_read": len(state.get("paper_insights", [])),
        "has_analysis": bool(state.get("analysis_report")),
        "has_draft": bool(state.get("draft_sections")),
        "critique_score": critique.get("score"),
        "critique_approved": critique.get("approved"),
        "critique_issues": critique.get("issues", [])[:3],
        "errors": state.get("errors", [])[-3:],
        "step_count": state.get("step_count", 0),
        "max_steps": state.get("max_steps", 12),
    }

def parse_decision(text: str) -> SupervisorDecision:
    text = (text or "").strip()

    match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        text,
        re.DOTALL
    )
    if match:
        text = match.group(1)

    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)

    return SupervisorDecision.model_validate(json.loads(text))


def fallback_decision(state: ResearchState) -> SupervisorDecision:
    """在 Supervisor 输出无法解析时，使用确定性策略维持工作流。"""
    if not state.get("paper_insights"):
        next_agent = "retrieval"
        objective = "搜索、筛选并阅读与用户问题相关的论文"
    elif not state.get("analysis_report"):
        next_agent = "analysis"
        objective = "比较论文证据并识别共识、矛盾与研究空白"
    elif not state.get("draft_sections"):
        next_agent = "writer"
        objective = "根据论文证据和分析结果生成研究报告"
    elif not state.get("critique"):
        next_agent = "critic"
        objective = "检查报告的完整性、证据与引用质量"
    else:
        next_agent = "finish"
        objective = "返回当前最佳研究报告"

    return SupervisorDecision(
        next_agent=next_agent,
        objective=objective,
        reason="Supervisor 输出无法解析，使用确定性兜底路由",
    )

async def supervisor(state: ResearchState) -> Command[ROUTES]:
    client = AsyncOpenAI(
        api_key=settings.anthropic_api_key,
        base_url=settings.base_url,
        timeout=60,
        max_retries=2,
    )

    summary = summarize_state(state)

    response = await client.chat.completions.create(
        model=settings.light_model or settings.default_model,
        max_tokens=500,
        messages=[
            {
                "role": "system",
                "content": """
                You are the supervisor of an academic research system.

                Available agents:
                - retrieval: search, screen and read academic papers
                - analysis: compare paper evidence and identify agreements or gaps
                - writer: write or revise the research report
                - critic: evaluate the report
                - finish: return the final answer

                Choose exactly one next agent.

                Return only JSON:
                {
                "next_agent": "retrieval|analysis|writer|critic|finish",
                "objective": "specific task for that agent",
                "reason": "why this agent should run next"
                }
                """,
            },
            {
                "role": "user",
                "content": json.dumps(summary, ensure_ascii=False),
            },
        ],
    )

    try:
        raw_decision = parse_decision(
            response.choices[0].message.content
        )
    except (json.JSONDecodeError, ValueError, TypeError):
        raw_decision = fallback_decision(state)
    safe_decision = validate_decision(raw_decision, state)

    return Command(
        goto=safe_decision.next_agent,
        update={
            "next_agent": safe_decision.next_agent,
            "current_task": safe_decision.objective,
            "decision_reason": safe_decision.reason,
            "finish_reason": (
                safe_decision.reason
                if safe_decision.next_agent == "finish"
                else state.get("finish_reason", "")
            ),
            "step_count": state.get("step_count", 0) + 1,
        }
    )
