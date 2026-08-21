from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime, timezone

from backend.db.connection import open_database
from backend.repositories import DatabaseFactory


class EvidenceRepository:
    def __init__(self, connection_factory: DatabaseFactory | None = None) -> None:
        self._connection_factory = connection_factory or open_database

    async def save_result_evidence(
        self,
        task_id: str,
        citations: Iterable[dict],
        evidence: Iterable[dict],
    ) -> None:
        database = await self._connection_factory()
        now = datetime.now(timezone.utc).isoformat()
        try:
            for citation in citations:
                await database.execute(
                    """
                    INSERT INTO report_citations(
                        citation_id, task_id, section_id, paper_id, claim_ids_json,
                        display_number, support_type, valid, validation_message,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(citation_id) DO UPDATE SET
                        section_id = excluded.section_id,
                        paper_id = excluded.paper_id,
                        claim_ids_json = excluded.claim_ids_json,
                        display_number = excluded.display_number,
                        support_type = excluded.support_type,
                        valid = excluded.valid,
                        validation_message = excluded.validation_message,
                        updated_at = excluded.updated_at
                    """,
                    (
                        citation["citation_id"],
                        task_id,
                        citation.get("section_id", ""),
                        citation.get("paper_id"),
                        json.dumps(citation.get("claim_ids", []), ensure_ascii=False),
                        citation.get("display_number"),
                        citation.get("support_type", "unverified"),
                        int(bool(citation.get("valid", False))),
                        citation.get("validation_message"),
                        now,
                        now,
                    ),
                )
            for item in evidence:
                await database.execute(
                    """
                    INSERT INTO paper_evidence(
                        evidence_id, task_id, paper_id, chunk_id, claim_id, excerpt,
                        content_type, page_start, page_end, support_type, verified,
                        validation_message, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(evidence_id) DO UPDATE SET
                        paper_id = excluded.paper_id,
                        chunk_id = excluded.chunk_id,
                        claim_id = excluded.claim_id,
                        excerpt = excluded.excerpt,
                        content_type = excluded.content_type,
                        page_start = excluded.page_start,
                        page_end = excluded.page_end,
                        support_type = excluded.support_type,
                        verified = excluded.verified,
                        validation_message = excluded.validation_message,
                        updated_at = excluded.updated_at
                    """,
                    (
                        item["evidence_id"],
                        task_id,
                        item["paper_id"],
                        item["chunk_id"],
                        item.get("claim_id"),
                        item["excerpt"],
                        item.get("content_type", "pdf"),
                        item.get("page_start"),
                        item.get("page_end"),
                        item.get("support_type", "unverified"),
                        int(bool(item.get("verified", False))),
                        item.get("validation_message"),
                        now,
                        now,
                    ),
                )
                for citation_id in item.get("citation_ids", []):
                    await database.execute(
                        """
                        INSERT INTO citation_evidence(citation_id, evidence_id, rank)
                        VALUES (?, ?, ?)
                        ON CONFLICT(citation_id, evidence_id) DO UPDATE SET rank = excluded.rank
                        """,
                        (citation_id, item["evidence_id"], item.get("rank", 0)),
                    )
            for citation in citations:
                for rank, evidence_id in enumerate(citation.get("evidence_ids", [])):
                    await database.execute(
                        """
                        INSERT INTO citation_evidence(citation_id, evidence_id, rank)
                        VALUES (?, ?, ?)
                        ON CONFLICT(citation_id, evidence_id) DO UPDATE SET rank = excluded.rank
                        """,
                        (citation["citation_id"], evidence_id, rank),
                    )
            await database.commit()
        except Exception:
            await database.rollback()
            raise
        finally:
            await database.close()

    async def list_for_task(self, task_id: str) -> dict[str, list[dict]]:
        database = await self._connection_factory()
        try:
            citation_cursor = await database.execute(
                "SELECT * FROM report_citations WHERE task_id = ? ORDER BY display_number, citation_id",
                (task_id,),
            )
            evidence_cursor = await database.execute(
                "SELECT * FROM paper_evidence WHERE task_id = ? ORDER BY evidence_id",
                (task_id,),
            )
            citations = []
            for row in await citation_cursor.fetchall():
                citations.append(
                    {
                        "citation_id": row["citation_id"],
                        "task_id": row["task_id"],
                        "section_id": row["section_id"],
                        "paper_id": row["paper_id"],
                        "claim_ids": json.loads(row["claim_ids_json"] or "[]"),
                        "display_number": row["display_number"],
                        "support_type": row["support_type"],
                        "valid": bool(row["valid"]),
                        "validation_message": row["validation_message"],
                        "evidence_ids": [],
                    }
                )
            relation_cursor = await database.execute(
                "SELECT citation_id, evidence_id FROM citation_evidence ORDER BY rank, evidence_id"
            )
            relations: dict[str, list[str]] = {}
            for relation in await relation_cursor.fetchall():
                relations.setdefault(relation["citation_id"], []).append(relation["evidence_id"])
            for citation in citations:
                citation["evidence_ids"] = relations.get(citation["citation_id"], [])
            evidence = [
                {
                    "evidence_id": row["evidence_id"],
                    "task_id": row["task_id"],
                    "paper_id": row["paper_id"],
                    "chunk_id": row["chunk_id"],
                    "claim_id": row["claim_id"],
                    "excerpt": row["excerpt"],
                    "content_type": row["content_type"],
                    "page_start": row["page_start"],
                    "page_end": row["page_end"],
                    "support_type": row["support_type"],
                    "verified": bool(row["verified"]),
                    "validation_message": row["validation_message"],
                }
                for row in await evidence_cursor.fetchall()
            ]
            return {"citations": citations, "evidence": evidence}
        finally:
            await database.close()
