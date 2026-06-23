"""最终报告渲染 — Markdown + 图表占位符处理"""
import re
import streamlit as st


def render_report(content: str, critique: dict | None = None, figures: list[dict] | None = None):
    """
    渲染最终研究报告。
    content: Markdown 文本（可能含 [[FIG:xxx]] 占位符）
    critique: 评审结果 {score, summary, issues}
    figures: 图表列表 [{id, path, caption}]
    """
    figures = figures or []
    fig_map = {f.get("id", ""): f for f in figures}

    if not content:
        st.warning("暂无报告内容")
        return

    # 处理 [[FIG:xxx]] 占位符（支持连字符等特殊字符）
    parts = re.split(r"\[\[FIG:([^\[\]]+)\]\]", content)

    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part.strip():
                st.markdown(part)
        else:
            fig = fig_map.get(part)
            if fig and fig.get("path"):
                st.image(fig["path"], caption=fig.get("caption", f"图表: {part}"))
            else:
                st.info(f"📊 图表 `{part}` 未生成")

    # 底部评审信息
    if critique and critique.get("score"):
        st.divider()
        score = critique.get("score", "?")
        summary = critique.get("summary", "")
        issues = critique.get("issues", [])

        st.markdown(f"**📊 质量评分: {score}/10**")
        if summary:
            st.caption(summary)
        if issues:
            with st.expander(f"查看 {len(issues)} 个问题"):
                for issue in issues:
                    st.markdown(f"- {issue}")
