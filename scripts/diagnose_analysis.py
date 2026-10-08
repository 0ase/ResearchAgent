"""Replay only analysis using a saved session, leaving its stored result unchanged."""
import argparse
import asyncio
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import uuid

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.agents.analyze import analyze_papers
from backend.config import settings
from backend.core.errors import error_payload
from backend.core.observability import configure_logging, log_context, logger
from backend.services.session_store import DB_PATH


def load_state(session_id: str | None) -> tuple[str, dict]:
    with closing(sqlite3.connect(f"file:{Path(DB_PATH).as_posix()}?mode=ro", uri=True)) as db:
        if session_id:
            row = db.execute("SELECT session_id, query, result_json FROM sessions WHERE session_id = ?",
                             (session_id,)).fetchone()
        else:
            row = db.execute("SELECT session_id, query, result_json FROM sessions ORDER BY created_at DESC LIMIT 1").fetchone()
    if not row:
        raise ValueError("No saved research session found")
    saved_id, query, raw = row
    result = json.loads(raw)
    objective = next((item.get("objective", "") for item in reversed(result.get("agent_trace", []))
                      if item.get("next_agent") == "analysis"), "")
    return saved_id, {"user_query": query, "paper_insights": result.get("paper_insights", []),
                      "current_task": objective}


async def run(session_id: str | None) -> int:
    saved_id, state = load_state(session_id)
    request_id = uuid.uuid4().hex
    with log_context(request_id=request_id, session_id=saved_id, stage="analysis", diagnostic=True):
        logger.info("analysis.diagnostic.started")
        try:
            result = await analyze_papers(state)
        except Exception as exc:
            print(json.dumps({"status": "failed", "session_id": saved_id, **error_payload(exc)}, ensure_ascii=False))
            return 1
        diagnostics = result["analysis_diagnostics"]
        print(json.dumps({"status": "completed", "session_id": saved_id, "request_id": request_id,
                          "analysis_call_id": diagnostics["analysis_call_id"], "counts": diagnostics["counts"],
                          "attempts_count": diagnostics["attempts_count"], "recovered": diagnostics["recovered"],
                          "finish_reason": diagnostics["finish_reason"], "response_id": diagnostics["response_id"]},
                         ensure_ascii=False))
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-id", help="Saved session ID; defaults to the most recent session")
    args = parser.parse_args()
    configure_logging(settings)
    sys.exit(asyncio.run(run(args.session_id)))
