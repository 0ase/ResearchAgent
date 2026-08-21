"""后端 API 客户端：HTTP + SSE 封装"""
import json
import os
from contextlib import AbstractContextManager

import httpx
from dotenv import load_dotenv

load_dotenv()
BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")


def health_check() -> bool:
    """健康检查，返回 True/False"""
    try:
        r = httpx.get(f"{BACKEND}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def stream_research(
    query: str,
    max_papers: int = 15,
) -> AbstractContextManager[httpx.Response]:
    """发起 SSE 流式研究请求，返回 httpx Response 对象"""
    return httpx.stream(
        "POST",
        f"{BACKEND}/api/research/stream",
        json={"query": query, "max_papers": max_papers},
        timeout=httpx.Timeout(connect=10, read=600, write=30, pool=30),
    )


def parse_sse(line: str) -> dict | None:
    """解析单行 SSE → dict，失败返回 None"""
    if not line or not line.startswith("data:"):
        return None
    data_str = line[5:].strip()
    if not data_str:
        return None
    try:
        return json.loads(data_str)
    except json.JSONDecodeError:
        return None


def get_history(limit: int = 20) -> list[dict]:
    """获取历史研究记录列表"""
    try:
        r = httpx.get(
            f"{BACKEND}/api/research/history",
            params={"limit": limit},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []


def get_session(session_id: str) -> dict | None:
    """获取某次研究的完整结果"""
    try:
        r = httpx.get(
            f"{BACKEND}/api/research/{session_id}",
            timeout=10,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def get_chat_messages(session_id: str, limit: int = 100) -> list[dict]:
    """获取某次研究的对话记录。"""
    try:
        r = httpx.get(
            f"{BACKEND}/api/research/{session_id}/messages",
            params={"limit": limit},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []


def ask_followup(session_id: str, message: str, message_id: str) -> dict:
    """向已有研究会话发送追问。异常交给界面展示。"""
    response = httpx.post(
        f"{BACKEND}/api/research/{session_id}/chat",
        json={"message": message, "message_id": message_id},
        timeout=180,
    )
    response.raise_for_status()
    return response.json()
