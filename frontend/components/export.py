"""导出按钮 — Markdown / BibTeX / 复制"""
import streamlit as st


def render_export(content: str, session_id: str = "report"):
    """渲染导出按钮行"""
    if not content:
        return

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="📥 下载 Markdown",
            data=content,
            file_name=f"review_{session_id}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with col2:
        bibtex = _generate_bibtex(content)
        st.download_button(
            label="📄 下载 BibTeX",
            data=bibtex,
            file_name=f"references_{session_id}.bib",
            mime="text/plain",
            use_container_width=True,
        )


def render_copy_block(content: str):
    """渲染一个可全选复制的代码块"""
    with st.expander("📋 查看原始 Markdown（可全选复制）"):
        st.code(content, language="markdown")


def _generate_bibtex(content: str) -> str:
    """从报告内容生成简易 BibTeX"""
    lines = []
    for line in content.split("\n"):
        line = line.strip()
        if line and line[0].isdigit():
            lines.append(line)
        if len(lines) >= 20:
            break

    entries = []
    for i, line in enumerate(lines[:20], 1):
        entry = (
            f"@article{{ref{i},\n"
            f'  title = {{{line}}},\n'
            f"  note = {{Extracted from research report}}\n"
            f"}}"
        )
        entries.append(entry)

    return "\n\n".join(entries) if entries else "% No references found"
