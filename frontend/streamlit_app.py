"""
📚 多Agent学术研究助手
7 Agent 协作流水线：Orchestrator → Search → Read → Analyze → Synthesize → Critic
"""
import streamlit as st
import httpx

from utils.api_client import health_check, stream_research, parse_sse, get_history, get_session
from utils.state import ensure_session, reset_session
from components.progress import (
    render_pipeline,
    stage_detail_orchestrate,
    stage_detail_search,
    stage_detail_filter,
    stage_detail_read,
    stage_detail_analyze,
    stage_detail_synthesize,
    stage_detail_critic,
)
from components.paper_table import render_paper_table
from components.report_viewer import render_report
from components.export import render_export, render_copy_block

# ============================================================
# Page Setup
# ============================================================
st.set_page_config(page_title="多Agent学术研究助手", page_icon="📚", layout="wide")

# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.title("⚙️ 配置")

    max_papers = st.slider("最大论文数", min_value=5, max_value=50, value=20, step=5)

    st.divider()

    if st.button("🩺 后端健康检查", use_container_width=True):
        if health_check():
            st.success("后端连接正常 ✅")
        else:
            st.error("无法连接后端 ❌")

    st.divider()

    # 历史记录
    st.subheader("📜 历史记录")
    history = get_history()
    if history:
        for item in history:
            label = f"{item.get('created_at', '')[:10]} — {item.get('query', '?')[:30]}"
            if st.button(
                label,
                key=f"hist_{item['session_id']}",
                use_container_width=True,
            ):
                full = get_session(item["session_id"])
                if full:
                    reset_session()
                    s = ensure_session()
                    s["query"] = full.get("query", "")
                    s["completed"] = True
                    s["session_id"] = item["session_id"]
                    result = full.get("result", {})
                    s["final_answer"] = result.get("final_answer", "")
                    s["papers"] = result.get("papers", [])
                    s["paper_insights"] = result.get("paper_insights", [])
                    s["analysis"] = result.get("analysis", {})
                    s["critique"] = result.get("critique", {})
                    s["current_stage"] = "critic"
                    st.rerun()
    else:
        st.caption("暂无历史记录")

    st.divider()
    st.caption("BIGONE v1.0")

# ============================================================
# Main
# ============================================================
st.title("📚 多Agent学术研究助手")
st.caption(
    "7 个专业化 Agent 协作：Orchestrator → Search → Read → Analyze → Synthesize → Critic"
)

tab1, tab2 = st.tabs(["🔬 研究", "📋 论文详情"])

# ============================================================
# Tab 1: 研究
# ============================================================
with tab1:
    query = st.chat_input("输入你的研究问题，例如：Transformer 注意力机制的最新进展有哪些？")

    s = ensure_session()

    if not query:
        # 没有新输入 → 展示已有结果（如果有的话）
        if s.get("completed") and s.get("final_answer"):
            st.divider()
            st.markdown("## 📝 研究报告")
            render_report(s["final_answer"], s.get("critique"))
            st.divider()
            render_export(s["final_answer"], s.get("session_id", "report"))
            render_copy_block(s["final_answer"])
        elif not s.get("is_running"):
            st.info("👆 在上方输入研究问题开始")
    else:
        # 新研究
        reset_session()
        s = ensure_session()
        s["query"] = query
        s["is_running"] = True

        st.chat_message("user").write(query)

        with st.chat_message("assistant"):
            progress_placeholder = st.empty()
            sub_query_placeholder = st.empty()
            final_placeholder = st.empty()

            stage_data_map: dict[str, str] = {}

            try:
                with stream_research(query, max_papers) as response:
                    if response.status_code != 200:
                        st.error(f"后端返回 {response.status_code}")
                        s["is_running"] = False
                        st.stop()

                    for line in response.iter_lines():
                        data = parse_sse(line)
                        if not data:
                            continue

                        event = data.get("event", "")
                        stage = data.get("stage", "")

                        # 更新进度
                        if stage == "orchestrate":
                            stage_data_map["orchestrate"] = stage_detail_orchestrate(data)
                            qs = data.get("sub_queries", [])
                            with sub_query_placeholder.container():
                                st.markdown("### 📋 研究计划")
                                for i, q in enumerate(qs, 1):
                                    st.write(f"{i}. {q}")

                        elif stage == "search":
                            stage_data_map["search"] = stage_detail_search(data)
                            preview = data.get("papers_preview", [])
                            if preview:
                                s["papers"] = preview

                        elif stage == "filter":
                            stage_data_map["filter"] = stage_detail_filter(data)
                            s["selected_papers"] = data.get("papers", [])

                        elif stage == "read":
                            stage_data_map["read"] = stage_detail_read(data)

                        elif stage == "analyze":
                            stage_data_map["analyze"] = stage_detail_analyze(data)

                        elif stage == "synthesize":
                            stage_data_map["synthesize"] = stage_detail_synthesize(data)

                        elif stage == "critic":
                            stage_data_map["critic"] = stage_detail_critic(data)

                        elif event == "done":
                            stage_data_map["critic"] = "✅ 完成"
                            s["completed"] = True
                            s["is_running"] = False
                            s["final_answer"] = data.get("final_answer", "")
                            s["critique"] = data.get("critique") or {}

                            all_papers = data.get("papers", [])
                            if all_papers:
                                s["papers"] = all_papers
                            s["paper_insights"] = data.get("paper_insights", [])
                            s["analysis"] = data.get("analysis", {})
                            s["session_id"] = data.get("session_id", "")

                            with final_placeholder.container():
                                st.divider()
                                st.markdown("## 📝 研究报告")
                                render_report(s["final_answer"], s.get("critique"))
                                st.divider()
                                render_export(s["final_answer"], s.get("session_id", "report"))
                                render_copy_block(s["final_answer"])

                        elif event == "error":
                            stage_data_map["error"] = f"❌ {data.get('message', '')}"
                            s["is_running"] = False

                        # 刷新进度时间线
                        s["current_stage"] = stage
                        with progress_placeholder.container():
                            render_pipeline(stage, stage_data_map)

            except httpx.ConnectError:
                progress_placeholder.error("❌ 无法连接后端，请确认 FastAPI 正在运行")
                s["is_running"] = False
            except Exception as e:
                progress_placeholder.error(f"❌ 异常: {e}")
                s["is_running"] = False

# ============================================================
# Tab 2: 论文详情
# ============================================================
with tab2:
    papers = s.get("papers", [])
    selected = s.get("selected_papers", [])
    insights = s.get("paper_insights", [])

    # 选中的 Top 20 论文（含 PDF 链接）
    if selected:
        st.subheader("⭐ 筛选后的论文 (Top 20)")
        st.caption("LLM 根据与问题的相关性评分选出")
        render_paper_table(selected)
        st.divider()

    if not papers and not selected:
        st.info("研究完成后，此处展示搜索到的论文详情")
    else:
        if papers:
            sources = ["all"] + sorted({p.get("source", "other") for p in papers})
            source_filter = st.selectbox("按来源筛选", sources, index=0)

            st.subheader("📚 全部搜索结果")
            render_paper_table(papers, source_filter=source_filter)

        if insights:
            st.divider()
            st.subheader("📖 论文深度摘要")
            for ins in insights:
                src = ins.get("source", "?")
                ans = ins.get("answer", "")
                with st.expander(f"**{src}** — {ans[:80]}...", expanded=False):
                    st.markdown(ans)
