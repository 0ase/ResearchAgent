from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel


CURRENT_INGESTION_VERSION = "chunk-v2"


class PaperChunk(BaseModel):
    chunk_id: str
    paper_id: str
    content: str
    chunk_index: int
    total_chunks: int
    page_start: int | None = None
    page_end: int | None = None
    content_type: Literal["pdf", "abstract"] = "pdf"
    ingestion_version: str = CURRENT_INGESTION_VERSION
    content_hash: str


class PaperEvidence(BaseModel):
    evidence_id: str
    task_id: str = ""
    paper_id: str
    chunk_id: str
    claim_id: str | None = None
    excerpt: str
    content_type: Literal["pdf", "abstract"] = "pdf"
    page_start: int | None = None
    page_end: int | None = None
    support_type: Literal["direct", "indirect", "unverified"] = "direct"
    verified: bool = False
    validation_message: str | None = None


def make_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def make_chunk_id(
    *,
    paper_id: str,
    ingestion_version: str,
    content_hash: str,
    chunk_index: int,
    page_start: int | None,
    page_end: int | None,
) -> str:
    identity = "|".join(
        [
            paper_id,
            ingestion_version,
            content_hash,
            str(chunk_index),
            str(page_start if page_start is not None else "abstract"),
            str(page_end if page_end is not None else "abstract"),
        ]
    )
    return f"chunk:{hashlib.sha256(identity.encode('utf-8')).hexdigest()}"
