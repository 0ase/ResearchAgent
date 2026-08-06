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
    if state.get("retrieval_exhausted") and not state.get("paper_insights"):
        next_agent = "finish"
        objective = "结束无法取得论文证据的研究任务"
    elif not state.get("paper_insights"):
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


def _decision_command(
    state: ResearchState,
    decision: SupervisorDecision,
) -> Command[ROUTES]:
    return Command(
        goto=decision.next_agent,
        update={
            "next_agent": decision.next_agent,
            "current_task": decision.objective,
            "decision_reason": decision.reason,
            "finish_reason": (
                decision.reason
                if decision.next_agent == "finish"
                else state.get("finish_reason", "")
            ),
            "step_count": state.get("step_count", 0) + 1,
        },
    )


async def supervisor(state: ResearchState) -> Command[ROUTES]:
    critique = state.get("critique") or {}
    if state.get("retrieval_exhausted") and not state.get("paper_insights"):
        return _decision_command(
            state,
            SupervisorDecision(
                next_agent="finish",
                objective="结束无法取得论文证据的研究任务",
                reason="检索已达到轮次上限且没有获得论文",
            ),
        )

    if (
        state.get("draft_sections")
        and critique
        and critique.get("approved") is not True
        and state.get("critique_round", 0) >= settings.max_critique_rounds
    ):
        return _decision_command(
            state,
            SupervisorDecision(
                next_agent="finish",
                objective="返回达到评审轮次上限后的最佳研究综述",
                reason="已达到最大质量评审轮次",
            ),
        )

    if state.get("draft_sections") and critique.get("approved") is True:
        # 已批准是确定性终止条件，不应再调用一次 Supervisor LLM。
        return _decision_command(
            state,
            SupervisorDecision(
                next_agent="finish",
                objective="返回已经通过质量评审的研究综述",
                reason="当前草稿已通过质量评审",
            ),
        )

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
                "content": (
                    "You are the supervisor of an academic research system.\n\n"
                    "Available agents:\n"
                    "- retrieval: search, screen and read academic papers\n"
                    "- analysis: compare paper evidence and identify agreements or gaps\n"
                    "- writer: write or revise the research report\n"
                    "- critic: evaluate the report\n"
                    "- finish: return the final answer\n\n"
                    "Choose exactly one next agent.\n\n"
                    "Return only JSON:\n"
                    '{\n'
                    '  "next_agent": "retrieval|analysis|writer|critic|finish",\n'
                    '  "objective": "specific task for that agent",\n'
                    '  "reason": "why this agent should run next"\n'
                    '}\n'
                ),
            },
            {
                "role": "user",
                "content": json.dumps(summary, ensure_ascii=False),
            },
        ]
    )

    try:
        raw_decision = parse_decision(
            response.choices[0].message.content
        )
    except (json.JSONDecodeError, ValueError, TypeError):
        raw_decision = fallback_decision(state)
    safe_decision = validate_decision(raw_decision, state)

    return _decision_command(state, safe_decision)
