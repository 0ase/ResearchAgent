"""Cheap candidate priority ordering; this never replaces relevance screening."""
from datetime import datetime, timezone
import html
import json
import math
from pathlib import Path
import re

from backend.config import settings
from backend.core.observability import report_exception

PRIORITY_WEIGHTS = {"topic_overlap": 50, "abstract": 25, "citations": 10,
                    "venue_quality": 10, "pdf_link": 5}
STOP_WORDS = set("a an the and or of to in on for with by from is are how what which "
                 "can do does research study studies review paper papers about".split())


def plain_text(value: object) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", str(value or ""))).strip()


def _terms(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-z][a-z0-9_-]*", text.casefold())) - STOP_WORDS
    for run in re.findall(r"[\u3400-\u9fff]+", text):
        tokens.update(run[i:i + 2] for i in range(len(run) - 1))
    return tokens


def citation_count(paper: dict) -> int | None:
    """Missing source coverage is not evidence of zero citations."""
    value = paper.get("citation_count")
    if paper.get("citation_count_known") is False or value is None:
        return None
    try:
        count = int(value)
    except (TypeError, ValueError):
        return None
    if count < 0:
        return None
    if count == 0 and "citation_count_known" not in paper and paper.get("source") in {"pubmed", "arxiv"}:
        return None
    return count


def _quality_key(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def _quality_record(record: object, year: int) -> dict | None:
    if not isinstance(record, dict):
        return None
    try:
        score = float(record["score"])
        metric_year = int(record["year"])
    except (KeyError, TypeError, ValueError):
        return None
    if (not math.isfinite(score) or not 0 <= score <= 100 or not 1900 <= metric_year <= year
            or not record.get("source") or not record.get("metric")):
        return None
    return {"score": score, "year": metric_year, "source": str(record["source"]),
            "metric": str(record["metric"])}


def _venue_metrics(year: int) -> dict[str, dict]:
    if not settings.venue_quality_path:
        return {}
    path = Path(settings.venue_quality_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Venue quality file must contain an object keyed by ISSN or venue name")
        return {_quality_key(key): record for key, value in data.items()
                if (record := _quality_record(value, year)) is not None}
    except (OSError, ValueError) as exc:
        report_exception(exc, "candidate_ranking.venue_quality.unavailable")
        return {}


def rank_candidate_papers(papers: list[dict], query: str) -> list[dict]:
    """Rank all candidates, with neutral values for unknown citation/venue metrics."""
    year = datetime.now(timezone.utc).year
    metrics = _venue_metrics(year)
    query_terms = _terms(query)
    texts = [(_terms(plain_text(p.get("title"))), _terms(plain_text(p.get("abstract"))))
             for p in papers]
    term_weights = {term: 1 + math.log((len(papers) + 1) /
                    (1 + sum(term in title or term in abstract for title, abstract in texts)))
                    for term in query_terms}
    denominator = sum(term_weights.values()) or 1
    citation_values = []
    for paper in papers:
        count = citation_count(paper)
        match = re.search(r"\b(19\d{2}|20\d{2})\b", str(paper.get("published_date") or ""))
        age = max(1, year - int(match[0]) + 1) if match else 1
        citation_values.append(math.log1p(count / age) if count is not None else None)
    citation_max = max((v for v in citation_values if v is not None), default=0) or 1
    ranked = []
    for paper, (title, abstract), citation_value in zip(papers, texts, citation_values):
        identifiers = [*(paper.get("issns") or []), paper.get("venue")]
        quality = next((metrics[_quality_key(key)] for key in identifiers
                        if _quality_key(key) in metrics), None)
        quality = quality or _quality_record(paper.get("venue_quality"), year)
        parts = {
            "topic_overlap": sum(weight * ((2 if term in title else 0) + (1 if term in abstract else 0))
                                 for term, weight in term_weights.items()) / (3 * denominator),
            "abstract": float(bool(plain_text(paper.get("abstract")))),
            "citations": citation_value / citation_max if citation_value is not None else 0.5,
            "venue_quality": quality["score"] / 100 if quality else 0.5,
            "pdf_link": float(str(paper.get("pdf_url") or "").startswith(("https://", "http://"))),
        }
        ranked.append({**paper, "citation_count_known": citation_count(paper) is not None,
                       "venue_quality": quality,
                       "candidate_priority_score": round(sum(PRIORITY_WEIGHTS[k] * v for k, v in parts.items()), 4),
                       "candidate_priority_details": parts})
    # Stable ties retain the source's retrieval order.
    return sorted(ranked, key=lambda paper: paper["candidate_priority_score"], reverse=True)
