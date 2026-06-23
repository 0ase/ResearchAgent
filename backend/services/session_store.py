"""SQLite 会话持久化：保存/加载研究历史"""
import json
import aiosqlite
from datetime import datetime

DB_PATH = "data/research.db"


async def _get_db():
    """获取数据库连接并确保表存在"""
    db = await aiosqlite.connect(DB_PATH)
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
    await db.commit()
    return db


async def save_session(session_id: str, query: str, result: dict):
    """保存或更新一次研究"""
    papers_count = len(result.get("papers", []))
    critique = result.get("critique") or {}
    score = str(critique.get("score", ""))
    result_json = json.dumps(result, ensure_ascii=False)

    db = await _get_db()
    await db.execute(
        "INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, query, datetime.now().isoformat(), papers_count, score, result_json),
    )
    await db.commit()
    await db.close()


async def get_sessions(limit: int = 20) -> list[dict]:
    """获取历史研究列表"""
    db = await _get_db()
    cursor = await db.execute(
        "SELECT session_id, query, created_at, papers_count, score "
        "FROM sessions ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    rows = await cursor.fetchall()
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
    cursor = await db.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    row = await cursor.fetchone()
    await db.close()
    if not row:
        return None
    return {
        "session_id": row[0],
        "query": row[1],
        "created_at": row[2],
        "papers_count": row[3],
        "score": row[4],
        "result": json.loads(row[5]),
    }
