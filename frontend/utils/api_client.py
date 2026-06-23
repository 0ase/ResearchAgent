"""后端 API 客户端：HTTP + SSE 封装"""
import json
import httpx

BACKEND = "http://localhost:8000"


def health_check() -> bool:
    """健康检查，返回 True/False"""
    try:
        r = httpx.get(f"{BACKEND}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def stream_research(query: str, max_papers: int = 20) -> httpx.Response:
    """发起 SSE 流式研究请求，返回 httpx Response 对象"""
    return httpx.stream(
        "POST",
        f"{BACKEND}/api/research/stream",
        json={"query": query, "max_papers": max_papers},
        timeout=600,
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
