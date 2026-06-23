"""7 阶段流水线进度 — 纵向时间线"""
import streamlit as st
from utils.state import PIPELINE_STAGES


def render_pipeline(current_stage: str, stage_data: dict[str, str]):
    """
    渲染纵向时间线。
    current_stage: 当前正在执行的 stage key（如 "search"）
    stage_data: {stage_key: "详情文字"}
    """
    current_idx = next(
        (i for i, (s, _, _) in enumerate(PIPELINE_STAGES) if s == current_stage),
        -1,
    )

    rows = []
    for i, (key, icon, label) in enumerate(PIPELINE_STAGES):
        detail = stage_data.get(key, "")

        if i < current_idx:
            status = "✅"
            title = f"~~{icon} **{label}**~~"
        elif i == current_idx:
            status = "⏳"
            title = f"{icon} **{label}**"
        else:
            status = "⬜"
            title = f"{icon} *{label}*"

        rows.append(f"| {status} | {title} | {detail} |")

    md = "|   | 阶段 | 详情 |\n"
    md += "|---|------|------|\n"
    md += "\n".join(rows)
    st.markdown(md)


def stage_detail_orchestrate(data: dict) -> str:
    qs = data.get("sub_queries", [])
    return f"拆解为 {len(qs)} 个子问题"


def stage_detail_search(data: dict) -> str:
    return (
        f"共 {data.get('total', 0)} 篇 "
        f"(arXiv:{data.get('arxiv', 0)} | "
        f"S2:{data.get('s2', 0)} | "
        f"PubMed:{data.get('pubmed', 0)} | "
        f"Crossref:{data.get('crossref', 0)})"
    )


def stage_detail_filter(data: dict) -> str:
    return f"筛选出 Top {data.get('count', 0)} 篇"


def stage_detail_read(data: dict) -> str:
    return f"已分析 {data.get('papers_read', 0)} 篇"


def stage_detail_analyze(data: dict) -> str:
    return (
        f"共识 {data.get('agreements', 0)} · "
        f"矛盾 {data.get('contradictions', 0)} · "
        f"研究空白 {data.get('gaps', 0)}"
    )


def stage_detail_synthesize(data: dict) -> str:
    return f"已生成 {data.get('length', 0)} 字符"


def stage_detail_critic(data: dict) -> str:
    score = data.get("score", "?")
    approved = data.get("approved", False)
    return f"{score}/10 — {'✅ 通过' if approved else '⚠️ 需改进'}"
