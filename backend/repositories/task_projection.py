"""A snapshot cursor and its complete event projection share one read transaction."""
import json
from datetime import datetime
from backend.api.schemas.tasks import StageSnapshot, ResearchStage, StageStatus


async def project_task(database, task):
    rows = await database.execute_fetchall(
        "SELECT * FROM task_events WHERE task_id = ? ORDER BY sequence", (task.id,))
    stages = {s.stage.value: s for s in task.stages}
    for row in rows:
        payload = json.loads(row["payload_json"] or "{}")
        task.replay_events.append({"schema_version": row["schema_version"],
            "task_id": task.id, "sequence": row["sequence"], "event_type": row["event_type"],
            "stage": row["stage"], "level": row["level"], "payload": payload,
            "occurred_at": row["occurred_at"]})
        task.last_sequence = row["sequence"]
        name = row["stage"]
        kind = row["event_type"]
        if name and kind.startswith("stage."):
            task.current_stage = ResearchStage(name)
            stage = stages.setdefault(name, StageSnapshot(stage=name))
            if kind == "stage.started":
                stages[name] = StageSnapshot(stage=name, status="running",
                    started_at=row["occurred_at"], attempt=payload.get("attempt", stage.attempt))
            elif kind == "stage.progress":
                task.progress.metrics.update(payload)
            elif kind in {"stage.completed", "stage.failed", "stage.warning"}:
                stage.status = StageStatus(kind.split(".")[1])
                if kind == "stage.completed":
                    stage.completed_at = datetime.fromisoformat(row["occurred_at"])
                    stage.duration_ms = payload.get("duration_ms")
    task.stages = list(stages.values())
    return task
