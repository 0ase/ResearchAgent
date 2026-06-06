from pydantic import BaseModel, Field
# 定义http请求的格式，返回的参数类型
class ResearchRequest(BaseModel):
    query: str = Field(..., description="research question")
    max_papers: int = Field(default=10, ge=1, le=50)

class ResearchResponse(BaseModel):
    session_id: str
    research_plan: list[dict]
    papers_count: int
    final_answer: str
