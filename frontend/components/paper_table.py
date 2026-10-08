"""paper list -- can be expanded and check abstract"""
import streamlit as st

def render_paper_table(papers: list[dict], source_filter: str = "all"):
    """    
    Render a collapsible list of papers.
    papers: List of papers
    source_filter: Filter by source ("all" / "arxiv" / "semantic_scholar" / "pubmed" / "crossref")
    """
    if not papers:
        st.info("No paper data available")
        return 
    
    # Screening
    if source_filter != "all":
        papers = [p for p in papers if p.get("source") == source_filter]

    # Top Statistics
    arxiv_n = sum(1 for p in papers if p.get("source") == "arxiv")
    s2_n = sum(1 for p in papers if p.get("source") == "semantic_scholar")
    pubmed_n = sum(1 for p in papers if p.get("source") == "pubmed")
    crossref_n = sum(1 for p in papers if p.get("source") == "crossref")

    st.caption(
        f"共 **{len(papers)}** 篇 | "
        f"arXiv: {arxiv_n} | S2: {s2_n} | PubMed: {pubmed_n} | Crossref: {crossref_n}"
    )

    for i, paper in enumerate(papers):
        title = paper.get("title", "Untitled")[:120]
        source = paper.get("source", "?")
        year = str(paper.get("published_date", ""))[:4] or "N/A"
        citations = paper.get("citation_count", 0)
        if paper.get("citation_count_known") is False:
            citations = "未知"
        authors = ", ".join((paper.get("authors") or [])[:3])
        abstract = (paper.get("abstract") or "No abstract available")[:800]
        pdf_url = paper.get("pdf_url", "")
        relevance_score = paper.get("relevance_score")
        score_scale = paper.get("relevance_score_scale", 5)
        has_score = relevance_score is not None and relevance_score != ""
        status = paper.get("screening_status")
        tier = paper.get("screening_tier")

        label_parts = [f"**{i + 1}.** {title}"]
        if has_score:
            label_parts.append(f"`{relevance_score}/{score_scale}`")
        if status == "not_evaluated":
            label_parts.append("`未评估`")
        elif status == "failed":
            label_parts.append("`评分失败`")
        elif tier == "supplemental":
            label_parts.append("`补充论文`")
        label_parts.append(f"`{source}`  {year}")
        label = "  ".join(label_parts)

        with st.expander(label, expanded=False):
            if authors:
                st.caption(f"**作者:** {authors}")
            if paper.get("venue"):
                st.caption("**期刊／会议:** " + paper["venue"])
            col1, col2, col3 = st.columns(3)
            col1.caption(f"**来源:** {source}")
            col2.caption(f"**引用:** {citations}")
            if has_score:
                col3.caption(f"**相关性:** {relevance_score}/{score_scale}")
            if tier == "supplemental":
                st.caption("候选评估后数量不足，放宽总分门槛纳入；核心相关性要求仍保留。")
            if paper.get("relevance_reason"):
                st.caption("筛选理由：" + paper["relevance_reason"])
            dimensions = paper.get("screening_scores") or {}
            if dimensions:
                labels = {"topic_match": "主题匹配", "question_alignment": "问题契合",
                          "methodology": "方法匹配", "evidence_quality": "证据强度",
                          "recency": "时效性", "information_completeness": "信息完整性"}
                st.caption(" · ".join(f"{labels[key]} {value:g}/5" for key, value in dimensions.items() if key in labels))
            if pdf_url:
                st.markdown(f"📄 [PDF 链接]({pdf_url})")
            st.markdown(f"> {abstract}")
