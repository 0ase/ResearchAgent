import json
import re
from difflib import SequenceMatcher
from typing import Literal

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from backend.agents.state import ResearchState
from backend.config import settings


class SearchReviewDecision(BaseModel):
    action: Literal["enough", "refine"]
    reason: str
    missing_topics: list[str] = Field(default_factory=list)
    new_queries: list[str] = Field(default_factory=list)


def _normalize_query(query: str) -> str:
    return " ".join(query.casefold().split())


def remove_duplicate_queries(
    new_queries: list[str],
    previous_queries: list[str],
    limit: int = 2,
) -> list[str]:
    """删除空查询、重复查询和高度相似的查询。"""
    known = [
        _normalize_query(query)
        for query in previous_queries
        if str(query).strip()
    ]
    result: list[str] = []

    for query in new_queries:
        cleaned = " ".join(str(query).split()).strip()
        if len(cleaned) < 5:
            continue

        normalized = _normalize_query(cleaned)
        duplicate = any(
            normalized == previous
            or SequenceMatcher(None, normalized, previous).ratio() >= 0.90
            for previous in known
        )
        if duplicate:
            continue

        result.append(cleaned)
        known.append(normalized)
        if len(result) >= limit:
            break

    return result


def _parse_json_object(text: str) -> dict:
    """兼容普通 JSON、Markdown JSON 代码块和前后说明文字。"""
    text = (text or "").strip()

    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else {}
    except json.JSONDecodeError:
        pass

    for pattern in (
        r"```(?:json)?\s*(\{.*?\})\s*```",
        r"\{.*\}",
    ):
        match = re.search(pattern, text, flags=re.DOTALL)
        if not match:
            continue
        candidate = match.group(1) if match.lastindex else match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    return {}


async def call_search_review_model(
    user_query: str,
    current_queries: list[str],
    previous_queries: list[str],
    papers: list[dict],
    search_round: int,
) -> SearchReviewDecision:
    """检查检索覆盖度，并在存在关键缺口时生成 1～2 个补充查询。"""
    paper_text = "\n\n".join(
        (
            f"[Paper {index}]\n"
            f"Title: {paper.get('title', '')}\n"
            f"Abstract: {(paper.get('abstract') or '')[:400]}"
        )
        for index, paper in enumerate(papers[:30], 1)
    ) or "No papers were found."

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
            {
                "role": "system",
                "content": (
                    "You review academic search coverage. Determine whether the "
                    "papers cover the original question's important topics, methods, "
                    "comparisons, empirical evidence, and limitations. Use action "
                    "'refine' only for a material evidence gap. When refining, create "
                    "1-2 concise English academic search queries that target the gaps "
                    "and do not repeat previous queries. Return ONLY JSON with keys: "
                    "action, reason, missing_topics, new_queries."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Original research question:\n{user_query}\n\n"
                    f"Search round:\n{search_round}\n\n"
                    "Queries in this round:\n"
                    f"{json.dumps(current_queries, ensure_ascii=False)}\n\n"
                    "Queries used before this round:\n"
                    f"{json.dumps(previous_queries, ensure_ascii=False)}\n\n"
                    f"Current papers:\n{paper_text}"
                ),
            },
        ],
    )

    data = _parse_json_object(response.choices[0].message.content or "")
    try:
        return SearchReviewDecision.model_validate(data)
    except (ValueError, TypeError):
        fallback_queries = remove_duplicate_queries(
            [
                f"{user_query} systematic review recent advances",
                f"{user_query} comparative evaluation benchmark",
                f"{user_query} limitations future directions",
            ],
            previous_queries + current_queries,
            limit=2,
        )
        should_refine = (
            len(papers) < settings.min_paper_default
            and bool(fallback_queries)
        )
        return SearchReviewDecision(
            action="refine" if should_refine else "enough",
            reason="Search Review 输出无法解析，使用确定性兜底策略",
            new_queries=fallback_queries if should_refine else [],
        )


async def review_search_results(state: ResearchState) -> dict:
    """审查搜索结果；需要补检时用新查询覆盖当前 research_plan。"""
    papers = state.get("raw_papers", [])
    plan = state.get("research_plan", [])
    search_round = state.get("search_round", 0)
    previous_queries = state.get("previous_queries", [])
    current_queries = [
        item.get("sub_query", "").strip()
        for item in plan
        if item.get("sub_query", "").strip()
    ]
    all_used_queries = list(dict.fromkeys(previous_queries + current_queries))

    # Search Agent 已经把轮次加一。到达上限后直接使用累计结果，
    # 不再生成一个永远不会执行的新计划。
    if search_round >= settings.max_search_rounds:
        action = "use_existing" if papers else "no_results"
        return {
            "previous_queries": all_used_queries,
            "search_review": {
                "action": action,
                "reason": "已达到最大搜索轮次",
                "missing_topics": [],
                "new_queries": [],
            },
            "search_gaps": [],
        }

    decision = await call_search_review_model(
        user_query=state.get("user_query", ""),
        current_queries=current_queries,
        previous_queries=previous_queries,
        papers=papers,
        search_round=search_round,
    )
    new_queries = remove_duplicate_queries(
        decision.new_queries,
        all_used_queries,
        limit=2,
    )

    if decision.action == "refine" and new_queries:
        return {
            # LangGraph 会先合并这个更新，再执行条件路由；因此下一次
            # Search Agent 读取到的是这些新查询，而不是上一轮查询。
            "research_plan": [
                {"sub_query": query, "status": "pending"}
                for query in new_queries
            ],
            "previous_queries": all_used_queries,
            "search_review": {
                "action": "refine",
                "reason": decision.reason,
                "missing_topics": decision.missing_topics,
                "new_queries": new_queries,
            },
            "search_gaps": decision.missing_topics,
        }

    action = "enough" if papers else "no_results"
    reason = decision.reason
    if decision.action == "refine" and not new_queries:
        reason = "没有生成有效且不重复的新查询"

    return {
        "previous_queries": all_used_queries,
        "search_review": {
            "action": action,
            "reason": reason,
            "missing_topics": decision.missing_topics,
            "new_queries": [],
        },
        "search_gaps": decision.missing_topics,
    }
