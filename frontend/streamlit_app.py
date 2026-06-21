import json
import streamlit as st
import httpx


st.set_page_config(page_title="多Agent学术研究助手", layout="wide")
st.title("📚 多Agent学术研究助手 — 7 Agent 协作")

# 输入框
query = st.chat_input("输入你的研究问题...")

if query:
    st.chat_message("user").write(query)

    # 用一个聊天消息承载所有进度
    with st.chat_message("assistant"):
        status_text = st.empty()
        progress_placeholder = st.empty()
        final_placeholder = st.empty()

        status_text.write("🤖 正在启动 7-Agent 流水线...")

        try:
            with httpx.stream(
                "POST",
                "http://localhost:8000/api/research/stream",
                json={"query": query, "max_papers": 20},
                timeout=600,
            ) as response:
                for line in response.iter_lines():
                    if not line:
                        continue
                    # SSE 格式：data:{json}\n\n
                    if not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if not data_str:
                        continue
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    stage = data.get("stage", "")
                    label = data.get("label", stage)

                    if stage == "orchestrate":
                        status_text.write(f"🧠 {label}")
                        qs = data.get("sub_queries", [])
                        progress_placeholder.markdown(
                            "### 📋 研究计划\n" +
                            "\n".join(f"{i}. {q}" for i, q in enumerate(qs, 1))
                        )

                    elif stage == "search":
                        status_text.write(f"🔍 {label}")
                        progress_placeholder.markdown(
                            f"### 📊 搜索完成\n"
                            f"**总计 {data.get('total', 0)} 篇** | "
                            f"arXiv: {data.get('arxiv', 0)} | "
                            f"S2: {data.get('s2', 0)} | "
                            f"PubMed: {data.get('pubmed', 0)} | "
                            f"Crossref: {data.get('crossref', 0)}"
                        )

                    elif stage == "read":
                        status_text.write(f"📖 {label}")
                        progress_placeholder.markdown(
                            f"### 📖 深度阅读\n已分析 **{data.get('papers_read', 0)}** 篇论文"
                        )

                    elif stage == "analyze":
                        status_text.write(f"🔬 {label}")
                        progress_placeholder.markdown(
                            f"### 🔬 对比分析\n"
                            f"共识: {data.get('agreements', 0)} | "
                            f"矛盾: {data.get('contradictions', 0)} | "
                            f"空白: {data.get('gaps', 0)}"
                        )

                    elif stage == "synthesize":
                        status_text.write(f"✍️ {label}")
                        progress_placeholder.markdown(
                            f"### ✍️ 综述撰写完成\n{data.get('length', 0)} 字符"
                        )

                    elif stage == "critic":
                        status_text.write(f"✅ {label}")
                        progress_placeholder.markdown(
                            f"### ✅ 评审\n"
                            f"**{data.get('score', '?')}/10** — "
                            f"{'✅ 通过' if data.get('approved') else '⚠️ 需改进'}"
                        )

                    elif data.get("event") == "done":
                        status_text.write("✅ 研究完成！")
                        final = data.get("final_answer", "")
                        score_info = ""
                        c = data.get("critique", {})
                        if c:
                            score_info = f"\n\n**评审: {c.get('score', '?')}/10**"
                        final_placeholder.markdown(final[:3000] + score_info if final else "暂无结果")

        except Exception as e:
            status_text.error(f"❌ 连接失败: {e}")
