import uuid
from fastapi import APIRouter
from backend.agents.graph import build_graph
from backend.api.schemas import ResearchRequest, ResearchResponse

router = APIRouter(prefix="/research", tags=["research"])

@router.post("/", response_model=ResearchResponse) # response_model定义了回复在客户端的显示，避免暴露不必要的信息
async def start_research(req: ResearchRequest):
    app = build_graph()
    """这里使用ainvoke异步传送到图的起始节点
    ainvoke接收一个字典作为流水线的初始状态
    long story in short, this is a entry of the langgraph"""
    result = await app.ainvoke({
        "user_query": req.query,
        "search_round": 0
    })

    return ResearchResponse(
        session_id=str(uuid.uuid4()),
        research_plan=result.get("research_plan", []),
        papers_count=len(result.get("raw_papers", [])),
        final_answer=result.get("final_answer", "Research Done")
    )