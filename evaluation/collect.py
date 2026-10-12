"""Read existing logs/database and optional observations without running research."""
from __future__ import annotations

import argparse
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import tempfile
import os
import time

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_PATHS = {"/api/research", "/api/research/stream"}
TERMINAL_ERRORS = {"request.failed", "request.rejected", "stage.failed",
                   "analysis.output.failed", "analysis.input.failed", "analysis.request.failed"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) and value >= 0 else None


def query_digest(query: str) -> str:
    return hashlib.sha256(" ".join(query.split()).encode("utf-8")).hexdigest()


def atomic_json(path: Path, value, *, allow_locked_rewrite=False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", suffix=".tmp", delete=False) as file:
            temporary = Path(file.name)
            json.dump(value, file, ensure_ascii=False, indent=2, allow_nan=False)
            file.write("\n")
        # Windows dev-server/file-scanner readers can briefly hold this file.
        # Retain the old complete snapshot until an atomic replacement succeeds.
        for attempt in range(6):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == 5:
                    if os.name == "nt" and allow_locked_rewrite and path.is_file():
                        # Some Windows readers allow writes but deny renames.
                        # Only validated public aggregates opt into this fallback;
                        # observations always retain the atomic write contract.
                        with path.open("w", encoding="utf-8") as destination:
                            destination.write(temporary.read_text(encoding="utf-8"))
                        break
                    raise
                time.sleep(0.03 * 2 ** attempt)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def result_summary(result: dict) -> dict:
    def entries(name):
        return [item for item in result.get(name, []) if isinstance(item, dict)] if isinstance(result.get(name), list) else []

    selected = [str(p.get("source_id")) for p in entries("selected_papers") if p.get("source_id")]
    read = list(dict.fromkeys(str(p.get("source")) for p in entries("paper_insights")
                              if p.get("source") and str(p.get("answer") or "").strip()))
    analysis = result.get("analysis_diagnostics") or {}
    if not isinstance(analysis, dict):
        analysis = {}
    return {
        "has_report": bool(str(result.get("final_answer") or "").strip()),
        "selected_available": isinstance(result.get("selected_papers"), list),
        "selected_paper_ids": selected, "read_paper_ids": read,
        "candidate_count": len(entries("papers")),
        "warning_count": len(result.get("warnings") or []),
        "writer_incomplete": bool(result.get("writer_incomplete")),
        "writer_attempts": number(result.get("writer_generation_attempts")),
        "analysis_attempts": number(analysis.get("attempts_count")),
        "analysis_recovered": bool(analysis.get("recovered")),
    }


def read_sessions(db: Path) -> tuple[list[dict], list[str]]:
    if not db.is_file():
        return [], ["会话数据库不存在；未推算历史任务耗时。"]
    sessions = []
    try:
        with closing(sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)) as connection:
            connection.execute("PRAGMA query_only = ON")
            rows = connection.execute("SELECT session_id, query, result_json FROM sessions")
            for sid, query, raw in rows:
                try:
                    result = json.loads(raw)
                    if not isinstance(result, dict):
                        raise ValueError()
                except (TypeError, ValueError):
                    sessions.append({"session_id": sid, "invalid": True})
                    continue
                sessions.append({"session_id": sid, "request_id": result.get("request_id"),
                                 "query_hash": query_digest(query), "result": result_summary(result)})
        return sessions, []
    except sqlite3.Error:
        return [], ["会话数据库只读读取失败；保留日志统计，不尝试写入或迁移。"]


def read_log_records(files: list[Path]) -> tuple[list[dict], dict]:
    records, seen = [], set()
    malformed, duplicates, loaded = 0, 0, 0
    for file in files:
        try:
            with file.open(encoding="utf-8-sig", errors="replace") as stream:
                loaded += 1
                for line in stream:
                    try:
                        record = json.loads(line)
                        if not isinstance(record, dict) or not isinstance(record.get("message"), str):
                            raise ValueError()
                    except ValueError:
                        malformed += 1
                        continue
                    signature = json.dumps(record, sort_keys=True, ensure_ascii=False)
                    if signature in seen:
                        duplicates += 1
                        continue
                    seen.add(signature)
                    records.append(record)
        except OSError:
            continue
    records.sort(key=lambda item: item.get("timestamp", ""))
    return records, {"log_files": loaded, "malformed_log_lines": malformed,
                     "duplicate_log_lines": duplicates}


def _historical_calls(records: list[dict]) -> list[dict]:
    calls, seen = [], set()
    for index, record in enumerate(records):
        if record["message"] not in {"screening.response", "analysis.response.received"}:
            continue
        key = record.get("response_id") or record.get("analysis_call_id") or (record.get("timestamp"), index)
        if key in seen:
            continue
        seen.add(key)
        calls.append({"call_id": str(key), "stage": record.get("stage"), "status": "completed",
                      "model": record.get("response_model") or record.get("model"),
                      "prompt_tokens": number(record.get("prompt_tokens")),
                      "completion_tokens": number(record.get("completion_tokens")),
                      "total_tokens": number(record.get("total_tokens"))})
    return calls


def historical_runs(records: list[dict], sessions: list[dict]) -> tuple[list[dict], dict]:
    grouped = defaultdict(list)
    start_counts = defaultdict(int)
    for record in records:
        if record.get("request_id"):
            grouped[(record["request_id"], record.get("process_id"))].append(record)
            if record["message"] == "request.started" and record.get("method") == "POST" and record.get("path", "").rstrip("/") in RESEARCH_PATHS:
                start_counts[record["request_id"]] += 1
    by_session = {row["session_id"]: row for row in sessions if not row.get("invalid")}
    by_request = defaultdict(list)
    for row in by_session.values():
        if row.get("request_id"):
            by_request[row["request_id"]].append(row)
    runs, rejected, ambiguous = [], 0, 0
    for (rid, _), group in grouped.items():
        starts = [r for r in group if r["message"] == "request.started" and r.get("method") == "POST"
                  and r.get("path", "").rstrip("/") in RESEARCH_PATHS]
        if not starts:
            continue
        # Reused request IDs cannot be attributed to one execution safely.
        if len(starts) != 1 or start_counts[rid] != 1:
            ambiguous += 1
            continue
        start = starts[0]
        group = [r for r in group if r.get("timestamp", "") >= start.get("timestamp", "")]
        stages = [r for r in group if r["message"].startswith("stage.") and r.get("stage")]
        if not any(r["message"] == "stage.started" for r in stages):
            rejected += 1
            continue
        session_ids = list(dict.fromkeys(r["session_id"] for r in group if r.get("session_id")))
        candidates = [by_session[sid] for sid in session_ids if sid in by_session] or by_request.get(rid, [])
        saved = candidates[0] if len(candidates) == 1 else None
        end = next((r for r in reversed(group) if r["message"] == "request.completed"), None)
        error = any(r["message"] in TERMINAL_ERRORS for r in group)
        cancelled = any(r["message"] == "research.cancelled" for r in group) or bool(end and end.get("outcome") == "cancelled")
        has_report = bool(saved and saved["result"]["has_report"])
        status = "incomplete"
        if has_report and not error and not cancelled:
            status = "completed"
        elif cancelled:
            status = "cancelled"
        elif end and (error or end.get("outcome") == "failed" or (number(end.get("status_code")) or 0) >= 400):
            status = "failed"
        duration = number(end.get("duration_ms")) if end else None
        summary = saved["result"] if saved else {}
        runs.append({"run_id": "historical:" + rid, "request_id": rid,
                     "session_id": saved["session_id"] if saved else next(iter(session_ids), None),
                     "query_hash": saved.get("query_hash") if saved else None,
                     "kind": "historical", "task_started": True, "status": status,
                     "started_at": start.get("timestamp"), "ended_at": end.get("timestamp") if end else None,
                     "server_elapsed_seconds": duration / 1000 if duration is not None else None,
                     "llm_calls": _historical_calls(group), "embedding_calls": [],
                     "usage_observed": False, "retrieval_observed": False, "retrievals": [],
                     "stage_events": [{"event": r["message"], "stage": r.get("stage"),
                                       "duration_ms": number(r.get("duration_ms"))} for r in stages],
                     "application_retry": any(r["message"] in {"screening.batch.retry_split", "analysis.output.retrying", "embedding.attempt.failed"} for r in group),
                     "degraded": bool(summary.get("warning_count") or summary.get("writer_incomplete")
                                      or any(r["message"] == "stage.degraded" for r in group)),
                     "result": summary})
    return runs, {"rejected_or_unstarted_requests": rejected, "ambiguous_request_ids": ambiguous}


def collect(log_files: list[Path], db: Path, observations: Path, since: str | None = None) -> dict:
    records, diagnostics = read_log_records(log_files)
    sessions, notes = read_sessions(db)
    runs, boundaries = historical_runs(records, sessions)
    diagnostics.update(boundaries)
    observed, invalid = [], 0
    if observations.is_dir():
        saved_by_id = {s.get("session_id"): s for s in sessions if not s.get("invalid")}
        for file in sorted(observations.glob("*.json")):
            try:
                item = json.loads(file.read_text(encoding="utf-8"))
                if item.get("schema_version") != 1 or item.get("kind") != "observed" or not isinstance(item.get("stage_events"), list):
                    raise ValueError()
                if item.get("task_started"):
                    saved = saved_by_id.get(item.get("session_id"))
                    if saved:
                        item["result"] = saved["result"]
                        item["query_hash"] = item.get("query_hash") or saved.get("query_hash")
                    observed.append(item)
            except (OSError, ValueError, TypeError, AttributeError):
                invalid += 1
    # Full observations replace the same log-derived run, never count it twice.
    observed_requests = {r.get("request_id") for r in observed if r.get("request_id")}
    observed_sessions = {r.get("session_id") for r in observed if r.get("session_id")}
    runs = [r for r in runs if r.get("request_id") not in observed_requests and r.get("session_id") not in observed_sessions] + observed
    unique = {}
    for run in runs:
        key = run.get("request_id") or run.get("run_id")
        if key:
            unique[key] = run
    runs = sorted(unique.values(), key=lambda r: r.get("started_at") or "")
    if since:
        cutoff = datetime.fromisoformat(since.replace("Z", "+00:00"))
        if cutoff.tzinfo is None:
            raise ValueError("--since must include a timezone")
        runs = [r for r in runs if r.get("started_at") and datetime.fromisoformat(r["started_at"]) >= cutoff]
    matched = {r.get("session_id") for r in runs}
    diagnostics.update({"session_reports": len(sessions), "database_only_reports": sum(s.get("session_id") not in matched for s in sessions),
                        "observed_runs": len(observed), "invalid_observations": invalid})
    if diagnostics["database_only_reports"]:
        notes.append("部分历史报告没有对应的完整日志，不纳入耗时和任务终态统计。")
    if any(r["kind"] == "historical" for r in runs):
        notes.append("开发历史包含多个版本、问题与配置；这些是本机运行观测，不能当作固定测试集基准。")
    return {"schema_version": 1, "collected_at": utc_now(), "runs": runs,
            "diagnostics": diagnostics, "notes": notes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", type=Path, default=ROOT / "logs")
    parser.add_argument("--db", type=Path, default=ROOT / "data/research.db")
    parser.add_argument("--observations", type=Path, default=ROOT / "evaluation/runs/observed")
    parser.add_argument("--since", help="ISO time with explicit timezone")
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/runs/collected.json")
    args = parser.parse_args()
    report = collect(list(args.logs.glob("backend.log*")), args.db, args.observations, args.since)
    atomic_json(args.output, report)
    print(f"Collected {len(report['runs'])} research runs; no model calls or database writes.")


if __name__ == "__main__":
    main()
