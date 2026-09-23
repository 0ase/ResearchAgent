def _fallback_report(
    *,
    query: str,
    output_language: str,
    insights: list[dict],
    findings: list[dict],
    claims: list[dict],
    citation_catalog: list[dict],
) -> str:
    """Build a readable report when a provider returns citation-only output."""
    is_zh = output_language.lower().startswith("zh")
    lines = [
        "# 研究综合报告" if is_zh else "# Research synthesis report",
        "",
        ("## 研究问题" if is_zh else "## Research question"),
        query.strip() or ("本次研究围绕已检索论文进行综合。" if is_zh else "This report synthesizes the retrieved papers."),
        "",
        ("## 主要发现" if is_zh else "## Key findings"),
    ]
    claim_by_id = {
        str(claim.get("claim_id")): claim
        for claim in claims
        if claim.get("claim_id")
    }
    added = 0
    for citation in citation_catalog:
        citation_claim_ids = citation.get("claim_ids") or []
        claim = (
            claim_by_id.get(str(citation_claim_ids[0]))
            if citation_claim_ids
            else None
        )
        statement = str((claim or {}).get("statement") or "").strip()
        if not statement:
            continue
        lines.append(
            f"- {statement} [[CITE:{citation['citation_id']}]]"
        )
        added += 1
    if not added:
        for insight in insights:
            answer = str(insight.get("answer") or "").strip()
            if answer:
                lines.append(f"- {answer}")
    if not any(line.startswith("-") for line in lines):
        lines.append(
            "- 已完成论文检索与证据整理，但模型未返回可引用的文字结论。"
            if is_zh
            else "- The papers were retrieved and evidence was collected, but no prose conclusion was returned."
        )
    lines.extend(
        [
            "",
            ("## 证据范围与局限" if is_zh else "## Evidence scope and limitations"),
            (
                f"本报告基于 {len(insights)} 篇已读取论文及其可追踪分块；部分来源或全文可能不可用。"
                if is_zh
                else f"This report is based on {len(insights)} readable papers and traceable chunks; some sources or full text may be unavailable."
            ),
        ]
    )
    return "\n".join(lines)
