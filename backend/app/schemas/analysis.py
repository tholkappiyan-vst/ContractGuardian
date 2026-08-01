from pydantic import BaseModel
from datetime import datetime


class ClauseResponse(BaseModel):
    id: str
    clause_index: int
    section_number: str | None
    title: str | None
    body: str
    category: str
    subcategory: str | None
    confidence: float
    risk_score: int | None
    is_standard: bool | None

    class Config:
        from_attributes = True


class EntityResponse(BaseModel):
    id: str
    entity_type: str
    value: str
    original_text: str
    normalized: dict | None
    confidence: float
    role: str | None

    class Config:
        from_attributes = True


class RiskScoreResponse(BaseModel):
    id: str
    clause_id: str | None
    scope: str
    score: int
    label: str
    category: str
    explanation: str
    consequence: str
    affected_party: str | None
    is_standard: bool | None
    standard_note: str | None

    class Config:
        from_attributes = True


class AnalysisResponse(BaseModel):
    id: str
    version: int
    status: str
    executive_summary: str | None
    contract_type: dict | None
    parties: list | None
    dates: dict | None
    payment_summary: dict | None
    obligations: dict | None
    risk_score: int | None
    risk_label: str | None
    risk_summary: str | None
    top_risks: list | None
    action_items: dict | None
    model_used: str | None
    processing_ms: int | None
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


class NegotiationResponse(BaseModel):
    id: str
    clause_id: str
    difficulty: str
    label: str
    original_text: str
    alternative_text: str
    explanation: str
    talking_points: list[str] | None
    likelihood: str | None

    class Config:
        from_attributes = True


class FullAnalysisResponse(BaseModel):
    analysis: AnalysisResponse
    clauses: list[ClauseResponse]
    entities: list[EntityResponse]
    risks: list[RiskScoreResponse]
    negotiations: list[NegotiationResponse]
