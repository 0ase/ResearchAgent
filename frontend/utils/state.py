import streamlit as st
PIPELINE_STAGES = [
    ("orchestrate", "🧠", "拆解研究问题"),
    ("search",      "🔍", "多源搜索论文"),
    ("filter",      "📑", "筛选论文"),
    ("read",        "📖", "深度阅读论文"),
    ("analyze",     "🔬", "跨论文对比分析"),
    ("synthesize",  "✍️", "撰写文献综述"),
    ("critic",      "✅", "质量评审"),
]

def init_session():
    st.session_state.research = {
        "query": "",
        "current_stage": "",
        "stage_data": {},
        "papers": [],
        "paper_insights": [],
        "analysis": {},
        "final_answer": "",
        "critique": {},
        "session_id": "",
        "is_running": False,
        "completed": False,
    }

def ensure_session():
    """ make sure the research session is inited"""
    if "research" not in st.session_state:
        init_session()
    return st.session_state.research

def reset_session():
    init_session()