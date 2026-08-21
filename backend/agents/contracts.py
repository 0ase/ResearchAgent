from typing import Literal

from pydantic import BaseModel, Field

AgentName = Literal[
    "retrieval",
    "analysis",
    "writer",
    "critic",
    "finish",
]

class AgentTask(BaseModel):
    objective: str
    inputs: list[str] = Field(default_factory=list)
    constraints: dict = Field(default_factory=dict)

class AgentResult(BaseModel):
    agent: str
    status: Literal["success", "partial", "failed"]
    summary: str
    artifacts: dict
    suggested_next: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

class SupervisorDecision(BaseModel):
    next_agent: AgentName
    objective: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    
