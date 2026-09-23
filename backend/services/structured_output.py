from __future__ import annotations

import json
import re
from typing import Any, Literal, TypeVar

from pydantic import AliasChoices, BaseModel, Field, ValidationError, field_validator


class PaperClaim(BaseModel):
    claim_id: str = Field(validation_alias=AliasChoices("claim_id", "id"))
    paper_id: str
    statement: str = Field(validation_alias=AliasChoices("statement", "text", "claim"))
    support_type: Literal["direct", "indirect", "inference", "unverified"] = "direct"
    chunk_ids: list[str] = Field(default_factory=list)
    evidence_text: str | None = Field(
        default=None,
        validation_alias=AliasChoices("evidence_text", "excerpt", "evidence"),
    )

    @field_validator("chunk_ids", mode="before")
    @classmethod
    def normalize_chunk_ids(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return [str(item) for item in value if item]


class PaperInsight(BaseModel):
    paper_id: str
    summary: str = Field(default="", validation_alias=AliasChoices("summary", "answer"))
    claims: list[PaperClaim] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)


class AnalysisFinding(BaseModel):
    finding_id: str = Field(validation_alias=AliasChoices("finding_id", "id"))
    kind: Literal["agreement", "contradiction", "method", "gap"]
    statement: str = Field(validation_alias=AliasChoices("statement", "text", "finding"))
    claim_ids: list[str] = Field(default_factory=list)
    paper_ids: list[str] = Field(default_factory=list)
    support_type: Literal["claim", "analysis_inference", "unverified"] = "claim"
    valid: bool = True


class AnalysisOutput(BaseModel):
    findings: list[AnalysisFinding] = Field(default_factory=list)


ModelType = TypeVar("ModelType", bound=BaseModel)


def parse_model_output(
    text: str,
    model: type[ModelType],
    *,
    fallback_paper_id: str | None = None,
) -> ModelType | None:
    """Parse a provider response with one local repair pass and a safe fallback."""
    data = _extract_json(text)
    if data is None:
        data = _extract_json(_repair_text(text))
    if data is not None:
        try:
            return model.model_validate(data)
        except ValidationError:
            repaired = _repair_json(data)
            if repaired is not None:
                try:
                    return model.model_validate(repaired)
                except ValidationError:
                    pass

    if model is PaperInsight and text.strip():
        return model.model_validate(
            {
                "paper_id": fallback_paper_id or "unknown",
                "summary": text.strip(),
                "claims": [],
                "limitations": [],
                "chunk_ids": [],
            }
        )
    return None


def parse_paper_insight_output(
    text: str, *, canonical_paper_id: str,
) -> tuple[PaperInsight, bool]:
    """Normalize provider aliases without letting model IDs replace canonical IDs."""
    data = _extract_json(text)
    if data is None:
        data = _extract_json(_repair_text(text))
    if not isinstance(data, dict):
        candidate = text.strip()
        summary = candidate if data is None and not candidate.startswith(("{", "[", "```")) else ""
        return PaperInsight(paper_id=canonical_paper_id, summary=summary), True

    summary = next((data[key].strip() for key in ("summary", "answer")
                    if isinstance(data.get(key), str) and data[key].strip()), "")
    claims = []
    degraded = False
    raw_claims = data.get("claims", [])
    if not isinstance(raw_claims, list):
        degraded = True
        raw_claims = []
    for number, raw in enumerate(raw_claims, 1):
        if not isinstance(raw, dict):
            degraded = True
            continue
        normalized = {**raw, "paper_id": canonical_paper_id}
        normalized["claim_id"] = raw.get("claim_id") or raw.get("id") or f"{canonical_paper_id}:claim:{number}"
        normalized["statement"] = raw.get("statement") or raw.get("claim") or raw.get("text")
        normalized["chunk_ids"] = raw.get("chunk_ids", raw.get("chunk_id", []))
        normalized["evidence_text"] = raw.get("evidence_text", raw.get("excerpt", raw.get("evidence")))
        if not isinstance(normalized["statement"], str) or not normalized["statement"].strip():
            degraded = True
            continue
        if not isinstance(normalized["chunk_ids"], (list, str)):
            degraded = True
            continue
        try:
            claims.append(PaperClaim.model_validate(normalized))
        except ValidationError:
            degraded = True
            continue
    limitations = data.get("limitations", [])
    if isinstance(limitations, str):
        limitations = [limitations]
    if not isinstance(limitations, list):
        degraded = True
        limitations = []
    if any(not isinstance(item, str) for item in limitations):
        degraded = True
    limitations = [item for item in limitations if isinstance(item, str) and item.strip()]
    chunk_ids = data.get("chunk_ids", [])
    if isinstance(chunk_ids, str):
        chunk_ids = [chunk_ids]
    if not isinstance(chunk_ids, list):
        chunk_ids = []
    return PaperInsight(
        paper_id=canonical_paper_id, summary=summary, claims=claims,
        limitations=limitations, chunk_ids=[c for c in chunk_ids if isinstance(c, str)],
    ), degraded or not bool(claims)


def validate_claims(
    claims: list[PaperClaim],
    chunks: dict[str, dict[str, Any]],
) -> list[PaperClaim]:
    validated: list[PaperClaim] = []
    for claim in claims:
        direct = claim.support_type == "direct"
        if not claim.chunk_ids:
            direct = False
        for chunk_id in claim.chunk_ids:
            chunk = chunks.get(chunk_id)
            if chunk is None or chunk.get("paper_id") != claim.paper_id:
                direct = False
                break
        if direct and claim.evidence_text:
            direct = any(
                claim.evidence_text in str(chunks[chunk_id].get("content", ""))
                for chunk_id in claim.chunk_ids
            )
        elif direct:
            direct = False
        validated.append(
            claim.model_copy(
                update={"support_type": claim.support_type if direct else "unverified"}
            )
        )
    return validated


def validate_analysis_findings(
    findings: list[AnalysisFinding],
    *,
    claim_ids: set[str],
    paper_ids: set[str],
) -> list[AnalysisFinding]:
    validated: list[AnalysisFinding] = []
    for finding in findings:
        known_claims = [claim_id for claim_id in finding.claim_ids if claim_id in claim_ids]
        known_papers = [paper_id for paper_id in finding.paper_ids if paper_id in paper_ids]
        valid = len(known_claims) == len(finding.claim_ids) and len(known_papers) == len(finding.paper_ids)
        if finding.kind == "agreement" and len(known_claims) < 2:
            valid = False
        if finding.kind != "gap" and not known_claims:
            valid = False
        validated.append(
            finding.model_copy(
                update={
                    "claim_ids": known_claims,
                    "paper_ids": known_papers,
                    "valid": valid,
                    "support_type": (
                        "analysis_inference"
                        if finding.kind == "gap"
                        else "claim" if valid else "unverified"
                    ),
                }
            )
        )
    return validated


def _extract_json(text: str) -> Any | None:
    candidate = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", candidate, re.IGNORECASE | re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    for opening, closing in (("{", "}"), ("[", "]")):
        start = candidate.find(opening)
        end = candidate.rfind(closing)
        if start >= 0 and end > start:
            try:
                return json.loads(candidate[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


def _repair_json(value: Any) -> Any | None:
    if not isinstance(value, str):
        return value
    repaired = re.sub(r",\s*([}\]])", r"\1", value)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        return None


def _repair_text(text: str) -> str:
    return re.sub(r",\s*([}\]])", r"\1", text)
