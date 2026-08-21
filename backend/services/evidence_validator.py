from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvidenceValidationResult(BaseModel):
    citations: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    invalid_count: int = 0


def validate_result_evidence(state: dict[str, Any]) -> EvidenceValidationResult:
    papers = state.get("papers") or state.get("raw_papers") or []
    paper_map = {
        paper.get("paper_id") or paper.get("id"): paper
        for paper in papers
        if paper.get("paper_id") or paper.get("id")
    }
    claim_map = {
        claim.get("claim_id"): claim
        for claim in (state.get("paper_claims") or [])
        if claim.get("claim_id")
    }
    chunk_map = {
        chunk.get("chunk_id"): chunk
        for chunk in (state.get("chunks") or [])
        if chunk.get("chunk_id")
    }
    warnings: list[str] = []
    normalized_evidence: list[dict[str, Any]] = []
    invalid_count = 0
    for raw in state.get("evidence", []) or []:
        item = dict(raw)
        errors = _validate_evidence_item(item, paper_map, claim_map, chunk_map)
        if errors:
            invalid_count += 1
            item["verified"] = False
            item["support_type"] = "unverified"
            item["validation_message"] = "; ".join(errors)
            warnings.append(f"Evidence {item.get('evidence_id', 'unknown')} unverified: {item['validation_message']}")
        else:
            item["verified"] = True
            item.setdefault("validation_message", None)
            item.setdefault("support_type", "direct")
            item.setdefault("content_type", chunk_map[item["chunk_id"]].get("content_type", "pdf"))
        normalized_evidence.append(item)

    evidence_map = {item.get("evidence_id"): item for item in normalized_evidence}
    normalized_citations: list[dict[str, Any]] = []
    for raw in state.get("citations", []) or []:
        item = dict(raw)
        errors: list[str] = []
        if not item.get("citation_id"):
            errors.append("missing citation id")
        if not item.get("section_id"):
            errors.append("missing section id")
        paper_id = item.get("paper_id")
        if paper_id and paper_id not in paper_map:
            errors.append("paper does not exist")
        for claim_id in item.get("claim_ids", []) or []:
            claim = claim_map.get(claim_id)
            if claim is None:
                errors.append(f"claim does not exist: {claim_id}")
            elif paper_id and claim.get("paper_id") != paper_id:
                errors.append(f"claim belongs to another paper: {claim_id}")
        evidence_ids = item.get("evidence_ids", []) or []
        for evidence_id in evidence_ids:
            evidence = evidence_map.get(evidence_id)
            if evidence is None:
                errors.append(f"evidence does not exist: {evidence_id}")
            elif not evidence.get("verified"):
                errors.append(f"evidence is unverified: {evidence_id}")
            elif paper_id and evidence.get("paper_id") != paper_id:
                errors.append(f"evidence belongs to another paper: {evidence_id}")
        item["valid"] = not errors
        if errors:
            item["support_type"] = "unverified"
            item["validation_message"] = "; ".join(errors)
            warnings.append(f"Citation {item.get('citation_id', 'unknown')} unverified: {item['validation_message']}")
        normalized_citations.append(item)

    return EvidenceValidationResult(
        citations=normalized_citations,
        evidence=normalized_evidence,
        warnings=warnings,
        invalid_count=invalid_count,
    )


def _validate_evidence_item(
    item: dict[str, Any],
    papers: dict[str, dict[str, Any]],
    claims: dict[str, dict[str, Any]],
    chunks: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    evidence_id = item.get("evidence_id")
    if not evidence_id:
        errors.append("missing evidence id")
    paper_id = item.get("paper_id")
    if paper_id not in papers:
        errors.append("paper does not exist")
    chunk_id = item.get("chunk_id")
    chunk = chunks.get(chunk_id)
    if chunk is None:
        errors.append("chunk does not exist")
        return errors
    if chunk.get("paper_id") != paper_id:
        errors.append("chunk belongs to another paper")
    claim_id = item.get("claim_id")
    if claim_id:
        claim = claims.get(claim_id)
        if claim is None:
            errors.append("claim does not exist")
        else:
            if claim.get("paper_id") != paper_id:
                errors.append("claim belongs to another paper")
            if chunk_id not in (claim.get("chunk_ids") or []):
                errors.append("chunk is not attached to claim")
    excerpt = item.get("excerpt", "")
    if not excerpt or excerpt not in str(chunk.get("content", "")):
        errors.append("direct excerpt not found in chunk")
    expected_content_type = chunk.get("content_type", "pdf")
    if item.get("content_type", expected_content_type) != expected_content_type:
        errors.append("content type does not match chunk")
    if expected_content_type == "abstract" and (
        item.get("page_start") is not None or item.get("page_end") is not None
    ):
        errors.append("abstract evidence cannot have a PDF page range")
    if expected_content_type != "abstract":
        chunk_start = chunk.get("page_start")
        chunk_end = chunk.get("page_end")
        page_start = item.get("page_start")
        page_end = item.get("page_end")
        if chunk_start is not None and (page_start is None or page_start < chunk_start):
            errors.append("page start is outside known chunk range")
        if chunk_end is not None and (page_end is None or page_end > chunk_end):
            errors.append("page end is outside known chunk range")
        if page_start is not None and page_end is not None and page_end < page_start:
            errors.append("page range is inverted")
    return errors
