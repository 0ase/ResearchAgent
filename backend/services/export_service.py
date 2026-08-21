from __future__ import annotations

import json
import re

from backend.api.schemas.results import ResearchTaskResult


def export_result(result: ResearchTaskResult, format_name: str) -> tuple[str, str, str]:
    if format_name == "markdown":
        return result.report_markdown, "text/markdown; charset=utf-8", "md"
    if format_name == "bibtex":
        return _to_bibtex(result), "text/plain; charset=utf-8", "bib"
    if format_name == "json":
        return (
            json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
            "application/json; charset=utf-8",
            "json",
        )
    raise ValueError(f"unsupported export format: {format_name}")


def _to_bibtex(result: ResearchTaskResult) -> str:
    entries: list[str] = []
    for index, paper in enumerate(result.papers, start=1):
        source_id = str(paper.get("source_id") or f"paper-{index}")
        key = re.sub(r"[^A-Za-z0-9]+", "-", source_id).strip("-") or f"paper-{index}"
        title = _bibtex_value(paper.get("title", "Untitled"))
        authors = " and ".join(paper.get("authors") or [])
        year = str(paper.get("published_date") or "")[:4]
        doi = paper.get("doi") or ""
        lines = [f"@article{{{key},", f"  title = {{{title}}},"]
        if authors:
            lines.append(f"  author = {{{_bibtex_value(authors)}}},")
        if year:
            lines.append(f"  year = {{{_bibtex_value(year)}}},")
        if doi:
            lines.append(f"  doi = {{{_bibtex_value(doi)}}},")
        lines.append("}")
        entries.append("\n".join(lines))
    return "\n\n".join(entries) if entries else "% No references found"


def _bibtex_value(value: object) -> str:
    return str(value).replace("{", "\\{").replace("}", "\\}")
