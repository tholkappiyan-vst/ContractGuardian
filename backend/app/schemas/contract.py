from pydantic import BaseModel
from datetime import datetime


class ContractCreate(BaseModel):
    title: str
    description: str | None = None
    org_id: str | None = None


class ContractResponse(BaseModel):
    id: str
    title: str
    description: str | None
    contract_type: str | None
    status: str
    language: str
    page_count: int | None
    word_count: int | None
    risk_score: int | None
    uploaded_at: datetime
    analyzed_at: datetime | None

    class Config:
        from_attributes = True


class ContractListResponse(BaseModel):
    contracts: list[ContractResponse]
    total: int


class DocumentResponse(BaseModel):
    id: str
    file_name: str
    file_type: str
    file_size: int
    ocr_used: bool
    ocr_confidence: float | None
    page_count: int | None

    class Config:
        from_attributes = True
