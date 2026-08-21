import re

from backend.config import settings


_REQUIRED_SECTION_GROUPS = {
    "研究空白与未来方向": (
        "research gap",
        "future direction",
        "future work",
        "研究空白",
        "研究不足",
        "未来方向",
        "未来研究",
        "未来展望",
    ),
    "结论": (
        "conclusion",
        "concluding remarks",
        "结论",
        "总结与展望",
    ),
    "参考文献": (
        "references",
        "bibliography",
        "参考文献",
        "参考资料",
    ),
}


def find_report_completeness_issues(
    report: str,
    finish_reason: str | None = None,
) -> list[str]:
    """Return deterministic completeness issues that do not need an LLM."""
    text = (report or "").strip()
    normalized = text.casefold()
    issues: list[str] = []

    if finish_reason == "length":
        issues.append("模型因输出长度上限而停止")

    if len(text) < settings.writer_min_characters:
        issues.append(
            f"正文仅有 {len(text)} 个字符，少于最低目标 "
            f"{settings.writer_min_characters} 个字符"
        )

    for section_name, markers in _REQUIRED_SECTION_GROUPS.items():
        if not any(marker in normalized for marker in markers):
            issues.append(f"缺少“{section_name}”部分")

    # A markdown report ending with a dangling heading is almost certainly cut off.
    if re.search(r"(?:^|\n)#{1,6}\s+[^\n]+\s*$", text):
        issues.append("报告结束于未展开的标题")

    return issues
