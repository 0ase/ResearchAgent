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

    if len(papers) > 50:
        st.warning(f"论文较多（{len(papers)} 篇），仅显示前 50 篇")
        papers = papers[:50]

    for i, paper in enumerate(papers):
        title = paper.get("title", "Untitled")[:120]
        source = paper.get("source", "?")
        year = str(paper.get("published_date", ""))[:4] or "N/A"
        citations = paper.get("citation_count", 0)
        authors = ", ".join((paper.get("authors") or [])[:3])
        abstract = (paper.get("abstract") or "No abstract available")[:800]
        pdf_url = paper.get("pdf_url", "")
        relevance_score = paper.get("relevance_score", "")

        label_parts = [f"**{i + 1}.** {title}"]
        if relevance_score:
            label_parts.append(f"`{relevance_score}/5`")
        label_parts.append(f"`{source}`  {year}")
        label = "  ".join(label_parts)

        with st.expander(label, expanded=False):
            if authors:
                st.caption(f"**作者:** {authors}")
            col1, col2, col3 = st.columns(3)
            col1.caption(f"**来源:** {source}")
            col2.caption(f"**引用:** {citations}")
            if relevance_score:
                col3.caption(f"**相关性:** {relevance_score}/5")
            if pdf_url:
                st.markdown(f"📄 [PDF 链接]({pdf_url})")
            st.markdown(f"> {abstract}")