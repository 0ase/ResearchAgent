from pydantic import BaseModel, Field, field_validator


# 定义http请求的格式，返回的参数类型
class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="research question")
    max_papers: int = Field(default=15, ge=3, le=15)

    @field_validator("query")
    @classmethod
    def reject_blank_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must not be blank")
        return value

class ResearchResponse(BaseModel):
    session_id: str
    research_plan: list[dict]
    papers_count: int
    final_answer: str

class FollowUpRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
    )
    message_id: str = Field(..., min_length=1, max_length=128)

    @field_validator("message", "message_id")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class FollowUpResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[str] = Field(default_factory=list)
    mode: str
