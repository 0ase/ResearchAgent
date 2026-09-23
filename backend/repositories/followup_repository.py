import hashlib
import json
from datetime import datetime, timezone

from backend.api.errors import ApiError
from backend.db.connection import open_database


def conflict(code):
    return ApiError(code, "Follow-up request conflicts with current task state", status_code=409)


class FollowUpRepository:
    def __init__(self, connection_factory=None):
        self._connection_factory = connection_factory or open_database

    async def _task(self, db, task_id):
        rows = await db.execute_fetchall("SELECT status FROM research_tasks WHERE id=? AND deleted_at IS NULL", (task_id,))
        if not rows:
            raise ApiError("TASK_NOT_FOUND", "Task not found", status_code=404)
        return rows[0]["status"]

    async def snapshot(self, task_id):
        db = await self._connection_factory()
        try:
            await db.execute("BEGIN")
            status = await self._task(db, task_id)
            rows = await db.execute_fetchall("SELECT * FROM research_messages WHERE task_id=? ORDER BY id", (task_id,))
            jobs = await db.execute_fetchall("SELECT * FROM followup_jobs WHERE task_id=?", (task_id,))
            messages = [{"message_id": r["message_id"], "role": r["role"], "content": r["content"],
                "citations": json.loads(r["citations_json"]), "created_at": r["created_at"]} for r in rows]
            job = dict(jobs[0]) if jobs and status in {"queued", "running", "cancelling", "completed"} else None
            return {"task_id": task_id, "task_status": status, "messages": messages, "pending": job}
        finally:
            await db.close()

    async def put(self, task_id, message_id, content):
        db = await self._connection_factory()
        try:
            await db.execute("BEGIN IMMEDIATE")
            status = await self._task(db, task_id)
            if status not in {"queued", "running", "completed"}:
                raise conflict("FOLLOWUP_TASK_UNAVAILABLE")
            digest = hashlib.sha256(content.encode()).hexdigest()
            prior = await db.execute_fetchall("SELECT content_hash FROM followup_requests WHERE task_id=? AND message_id=?", (task_id, message_id))
            if prior and prior[0][0] != digest:
                raise conflict("MESSAGE_ID_CONFLICT")
            jobs = await db.execute_fetchall("SELECT * FROM followup_jobs WHERE task_id=?", (task_id,))
            if prior:
                # Retransmission never revives a replaced/cancelled/completed request.
                await db.commit()
                return
            if jobs and jobs[0]["status"] == "processing":
                raise conflict("FOLLOWUP_IN_PROGRESS")
            await db.execute("INSERT INTO followup_requests VALUES (?,?,?)", (task_id,message_id,digest))
            await db.execute("INSERT INTO followup_jobs VALUES (?,?,?,'queued',NULL,?) ON CONFLICT(task_id) DO UPDATE SET message_id=excluded.message_id,content=excluded.content,status='queued',error_code=NULL,created_at=excluded.created_at",
                (task_id,message_id,content,datetime.now(timezone.utc).isoformat()))
            await db.commit()
        finally:
            await db.close()

    async def cancel(self, task_id):
        db = await self._connection_factory()
        try:
            await db.execute("BEGIN IMMEDIATE")
            await self._task(db, task_id)
            jobs = await db.execute_fetchall("SELECT status FROM followup_jobs WHERE task_id=?", (task_id,))
            if jobs and jobs[0][0] == "processing":
                raise conflict("FOLLOWUP_IN_PROGRESS")
            await db.execute("DELETE FROM followup_jobs WHERE task_id=?", (task_id,))
            await db.commit()
        finally:
            await db.close()

    async def recover(self):
        db = await self._connection_factory()
        try:
            await db.execute("BEGIN IMMEDIATE")
            # Recover the narrow crash window between terminal status and its event.
            await db.execute("""INSERT INTO task_events(task_id,sequence,schema_version,event_type,stage,level,payload_json,occurred_at)
                SELECT t.id,(SELECT COALESCE(MAX(sequence),0)+1 FROM task_events WHERE task_id=t.id),1,'task.completed',NULL,'info','{}',COALESCE(t.completed_at,t.created_at)
                FROM research_tasks t JOIN research_results r ON r.task_id=t.id
                WHERE t.status='completed' AND t.deleted_at IS NULL AND t.client_request_id NOT LIKE 'legacy:%'
                AND NOT EXISTS(SELECT 1 FROM task_events e WHERE e.task_id=t.id AND e.event_type='task.completed')""")
            await db.execute("UPDATE followup_jobs SET status='queued' WHERE status='processing'")
            await db.execute("DELETE FROM followup_jobs WHERE task_id IN (SELECT id FROM research_tasks WHERE status IN ('failed','cancelled','interrupted') OR deleted_at IS NOT NULL)")
            await db.commit()
        finally:
            await db.close()

    async def claim(self):
        db = await self._connection_factory()
        try:
            await db.execute("BEGIN IMMEDIATE")
            await db.execute("DELETE FROM followup_jobs WHERE task_id IN (SELECT id FROM research_tasks WHERE status IN ('failed','cancelled','interrupted') OR deleted_at IS NOT NULL)")
            rows = await db.execute_fetchall("SELECT j.* FROM followup_jobs j JOIN research_tasks t ON t.id=j.task_id JOIN research_results r ON r.task_id=t.id WHERE j.status='queued' AND t.status='completed' AND t.deleted_at IS NULL AND (t.client_request_id LIKE 'legacy:%' OR EXISTS(SELECT 1 FROM task_events e WHERE e.task_id=t.id AND e.event_type='task.completed')) ORDER BY j.created_at LIMIT 1")
            job = dict(rows[0]) if rows else None
            if job:
                await db.execute("UPDATE followup_jobs SET status='processing' WHERE task_id=?", (job["task_id"],))
            await db.commit()
            return job
        finally:
            await db.close()

    async def finish(self, job, answer=None):
        db = await self._connection_factory()
        try:
            await db.execute("BEGIN IMMEDIATE")
            if answer is None:
                await db.execute("UPDATE followup_jobs SET status='failed',error_code='FOLLOWUP_FAILED' WHERE task_id=? AND message_id=?", (job["task_id"],job["message_id"]))
            else:
                for role, content, citations in (("user",job["content"],[]),("assistant",answer["answer"],answer.get("citations",[]))):
                    await db.execute("INSERT OR IGNORE INTO research_messages(task_id,message_id,role,content,citations_json,created_at) VALUES(?,?,?,?,?,?)",
                        (job["task_id"],job["message_id"],role,content,json.dumps(citations),datetime.now(timezone.utc).isoformat()))
                await db.execute("DELETE FROM followup_jobs WHERE task_id=? AND message_id=?", (job["task_id"],job["message_id"]))
            await db.commit()
        finally:
            await db.close()
