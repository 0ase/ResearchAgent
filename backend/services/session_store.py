"""SQLite 会话持久化：保存/加载研究历史"""
import json
from datetime import datetime
from pathlib import Path

import aiosqlite

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = str(PROJECT_ROOT / "data" / "research.db")


async def _get_db():
    """获取数据库连接并确保表存在"""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    try:
        await db.execute("PRAGMA busy_timeout = 5000")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                created_at TEXT NOT NULL,
                papers_count INTEGER DEFAULT 0,
                score TEXT DEFAULT '',
                result_json TEXT DEFAULT '{}'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE NOT NULL,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                citations_json TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            )
        """)
        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_session_id_id
            ON messages(session_id, id)
            """
        )
        await db.commit()
        return db
    except Exception:
        await db.close()
        raise


async def save_session(session_id: str, query: str, result: dict):
    """保存或更新一次研究"""
    papers_count = len(result.get("papers", []))
    critique = result.get("critique") or {}
    score = str(critique.get("score", ""))
    result_json = json.dumps(result, ensure_ascii=False)

    db = await _get_db()
    try:
        created_at = datetime.now().isoformat()
        await db.execute(
            """
            INSERT INTO sessions
                (session_id, query, created_at, papers_count, score, result_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                query = excluded.query,
                papers_count = excluded.papers_count,
                score = excluded.score,
                result_json = excluded.result_json
            """,
            (session_id, query, created_at, papers_count, score, result_json),
        )

        # 把原始问题和报告也作为会话的前两条消息保存。
        await db.execute(
            """
            INSERT OR IGNORE INTO messages
                (message_id, session_id, role, content, citations_json, created_at)
            VALUES (?, ?, 'user', ?, '[]', ?)
            """,
            (f"{session_id}:initial:user", session_id, query, created_at),
        )
        final_answer = str(result.get("final_answer") or "").strip()
        if final_answer:
            await db.execute(
                """
                INSERT OR IGNORE INTO messages
                    (message_id, session_id, role, content, citations_json, created_at)
                VALUES (?, ?, 'assistant', ?, '[]', ?)
                """,
                (
                    f"{session_id}:initial:assistant",
                    session_id,
                    final_answer,
                    created_at,
                ),
            )
        await db.commit()
    finally:
        await db.close()


async def get_sessions(limit: int = 20) -> list[dict]:
    """获取历史研究列表"""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT session_id, query, created_at, papers_count, score "
            "FROM sessions ORDER BY created_at DESC LIMIT ?",
            (max(1, min(limit, 100)),),
        )
        rows = await cursor.fetchall()
    finally:
        await db.close()
    return [
        {
            "session_id": r[0],
            "query": r[1],
            "created_at": r[2],
            "papers_count": r[3],
            "score": r[4],
        }
        for r in rows
    ]


async def get_session(session_id: str) -> dict | None:
    """获取某次研究的完整结果"""
    db = await _get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()
    if not row:
        return None
    try:
        result = json.loads(row[5])
    except (TypeError, json.JSONDecodeError):
        result = {}
    return {
        "session_id": row[0],
        "query": row[1],
        "created_at": row[2],
        "papers_count": row[3],
        "score": row[4],
        "result": result,
    }

async def add_message(
    session_id: str,
    message_id: str,
    role: str,
    content: str,
    citations: list[str] | None = None,
) -> int | None:
    """保存一条会话消息；相同 message_id 的重试不会重复写入。"""
    if role not in {"user", "assistant"}:
        raise ValueError(f"unsupported message role: {role}")

    db = await _get_db()
    try:
        cursor = await db.execute(
            """
            INSERT OR IGNORE INTO messages
                (message_id, session_id, role, content, citations_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                session_id,
                role,
                content,
                json.dumps(citations or [], ensure_ascii=False),
                datetime.now().isoformat(),
            ),
        )
        await db.commit()
        return cursor.lastrowid if cursor.rowcount else None
    finally:
        await db.close()


async def get_message(message_id: str) -> dict | None:
    """按客户端消息 ID 获取消息，用于安全处理请求重试。"""
    db = await _get_db()
    try:
        cursor = await db.execute(
            """
            SELECT message_id, session_id, role, content, citations_json, created_at
            FROM messages WHERE message_id = ?
            """,
            (message_id,),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()

    return _message_from_row(row) if row else None

async def get_messages(
    session_id: str,
    limit: int = 20,
) -> list[dict]:
    """按时间正序返回最近的消息，便于直接交给 LLM 和前端。"""
    db = await _get_db()
    try:
        cursor = await db.execute(
            """
            SELECT message_id, session_id, role, content, citations_json, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        )
        rows = await cursor.fetchall()
    finally:
        await db.close()

    return [_message_from_row(row) for row in reversed(rows)]


def _message_from_row(row) -> dict:
    try:
        citations = json.loads(row[4] or "[]")
    except (TypeError, json.JSONDecodeError):
        citations = []

    return {
        "message_id": row[0],
        "session_id": row[1],
        "role": row[2],
        "content": row[3],
        "citations": citations if isinstance(citations, list) else [],
        "created_at": row[5],
    }
