import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY
from app.core.database import Base


class Clause(Base):
    __tablename__ = "clauses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id: Mapped[str] = mapped_column(String, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    clause_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_number: Mapped[str | None] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subcategory: Mapped[str | None] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    is_standard: Mapped[bool | None] = mapped_column(Boolean)
    parent_id: Mapped[str | None] = mapped_column(String, ForeignKey("clauses.id", ondelete="SET NULL"))
    page_number: Mapped[int | None] = mapped_column(Integer)
    start_offset: Mapped[int | None] = mapped_column(Integer)
    end_offset: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    contract = relationship("Contract", back_populates="clauses")
    entities = relationship("Entity", back_populates="clause")
    risks = relationship("RiskScore", back_populates="clause")
    negotiations = relationship("NegotiationSuggestion", back_populates="clause")


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id: Mapped[str] = mapped_column(String, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    clause_id: Mapped[str | None] = mapped_column(String, ForeignKey("clauses.id", ondelete="SET NULL"), index=True)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized: Mapped[dict | None] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    role: Mapped[str | None] = mapped_column(String)
    aliases: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    contract = relationship("Contract", back_populates="entities")
    clause = relationship("Clause", back_populates="entities")


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id: Mapped[str] = mapped_column(String, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    clause_id: Mapped[str | None] = mapped_column(String, ForeignKey("clauses.id", ondelete="CASCADE"), index=True)
    scope: Mapped[str] = mapped_column(String, nullable=False)  # clause, contract, compounding
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    consequence: Mapped[str] = mapped_column(Text, nullable=False)
    affected_party: Mapped[str | None] = mapped_column(String)
    is_standard: Mapped[bool | None] = mapped_column(Boolean)
    standard_note: Mapped[str | None] = mapped_column(Text)
    related_clauses: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    contract = relationship("Contract", back_populates="risk_scores")
    clause = relationship("Clause", back_populates="risks")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id: Mapped[str] = mapped_column(String, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String, default="pending")
    executive_summary: Mapped[str | None] = mapped_column(Text)
    contract_type: Mapped[dict | None] = mapped_column(JSON)
    parties: Mapped[list | None] = mapped_column(JSON)
    dates: Mapped[dict | None] = mapped_column(JSON)
    payment_summary: Mapped[dict | None] = mapped_column(JSON)
    obligations: Mapped[dict | None] = mapped_column(JSON)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    risk_label: Mapped[str | None] = mapped_column(String)
    risk_summary: Mapped[str | None] = mapped_column(Text)
    top_risks: Mapped[list | None] = mapped_column(JSON)
    action_items: Mapped[dict | None] = mapped_column(JSON)
    model_used: Mapped[str | None] = mapped_column(String)
    prompt_version: Mapped[str | None] = mapped_column(String)
    tokens_input: Mapped[int | None] = mapped_column(Integer)
    tokens_output: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    processing_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    contract = relationship("Contract", back_populates="analyses")


class NegotiationSuggestion(Base):
    __tablename__ = "negotiation_suggestions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_id: Mapped[str] = mapped_column(String, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    clause_id: Mapped[str] = mapped_column(String, ForeignKey("clauses.id", ondelete="CASCADE"), nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    alternative_text: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    talking_points: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    likelihood: Mapped[str | None] = mapped_column(String)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    contract = relationship("Contract", back_populates="negotiations")
    clause = relationship("Clause", back_populates="negotiations")
