from pydantic import BaseModel
from datetime import datetime


class ChatRequest(BaseModel):
    message: str


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    citations: list | None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageResponse]
    contract_id: str


class ComparisonRequest(BaseModel):
    contract_id_a: str
    contract_id_b: str


class ComparisonDifference(BaseModel):
    category: str
    significance: str
    contract_a: str
    contract_b: str
    impact: str
    favors: str


class ComparisonResponse(BaseModel):
    summary: str
    recommendation: str
    confidence: float
    risk_a: int
    risk_b: int
    differences: list[ComparisonDifference]
    unchanged: list[str]
