from __future__ import annotations

import json
from datetime import datetime, timezone

from backend.api.schemas.results import ResearchTaskResult
from backend.db.connection import open_database
from backend.repositories import DatabaseFactory


class ResultRepository:
    def __init__(self, connection_factory: DatabaseFactory | None = None) -> None:
        self._connection_factory = connection_factory or open_database

    async def upsert(self, result: ResearchTaskResult) -> ResearchTaskResult:
        database = await self._connection_factory()
        now = datetime.now(timezone.utc).isoformat()
        try:
            await database.execute(
                """
                INSERT INTO research_results(
                    task_id, report_markdown, analysis_json, critique_json,
                    statistics_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    report_markdown = excluded.report_markdown,
                    analysis_json = excluded.analysis_json,
                    critique_json = excluded.critique_json,
                    statistics_json = excluded.statistics_json,
                    updated_at = excluded.updated_at
                """,
                (
                    result.task_id,
                    result.report_markdown,
                    json.dumps(result.analysis, ensure_ascii=False),
                    json.dumps(result.critique, ensure_ascii=False),
                    json.dumps(
                        {
                            "statistics": result.statistics,
                            "research_plan": result.research_plan,
                            "papers": result.papers,
                            "paper_insights": result.paper_insights,
                            "paper_claims": result.paper_claims,
                            "analysis_findings": result.analysis_findings,
                            "structured_report": result.structured_report,
                            "evidence": result.evidence,
                            "citations": result.citations,
                            "partial": result.partial,
                            "warnings": result.warnings,
                            "capabilities": result.capabilities.model_dump(),
                        },
                        ensure_ascii=False,
                    ),
                    now,
                    now,
                ),
            )
            await database.commit()
            return result
        finally:
            await database.close()

    async def get(self, task_id: str) -> ResearchTaskResult | None:
        database = await self._connection_factory()
        try:
            cursor = await database.execute(
                "SELECT * FROM research_results WHERE task_id = ?",
                (task_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            statistics = json.loads(row["statistics_json"] or "{}")
            return ResearchTaskResult(
                task_id=row["task_id"],
                report_markdown=row["report_markdown"],
                analysis=json.loads(row["analysis_json"] or "{}"),
                critique=json.loads(row["critique_json"] or "{}"),
                statistics=statistics.get("statistics", {}),
                research_plan=statistics.get("research_plan", []),
                papers=statistics.get("papers", []),
                paper_insights=statistics.get("paper_insights", []),
                paper_claims=statistics.get("paper_claims", []),
                analysis_findings=statistics.get("analysis_findings", []),
                structured_report=statistics.get("structured_report", {}),
                evidence=statistics.get("evidence", []),
                citations=statistics.get("citations", []),
                partial=statistics.get("partial", False),
                warnings=statistics.get("warnings", []),
                capabilities=statistics.get("capabilities", {}),
            )
        finally:
            await database.close()
