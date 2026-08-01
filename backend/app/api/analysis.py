from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.exceptions import NotFoundError, ForbiddenError, BadRequestError
from app.models.user import User
from app.models.contract import Contract
from app.models.analysis import Clause, Entity, RiskScore, Analysis, NegotiationSuggestion
from app.schemas.analysis import (
    FullAnalysisResponse, AnalysisResponse,
    ClauseResponse, EntityResponse, RiskScoreResponse, NegotiationResponse,
)
from app.services import analysis as analysis_service, audit as audit_service

router = APIRouter()


async def _get_user_contract(contract_id: str, user: User, db: AsyncSession) -> Contract:
    contract = await db.get(Contract, contract_id)
    if not contract or contract.deleted_at:
        raise NotFoundError("Contract")
    if contract.user_id != user.id:
        raise ForbiddenError()
    return contract


@router.post("/{contract_id}/analyze", response_model=AnalysisResponse)
async def trigger_analysis(
    contract_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contract = await _get_user_contract(contract_id, user, db)

    if contract.status == "analyzing":
        raise BadRequestError("Analysis already in progress")

    analysis = await analysis_service.run_analysis(contract_id, db)

    await audit_service.log_action(
        db, action="contract.analyze", resource_type="contract",
        user_id=user.id, contract_id=contract_id,
        details={"analysis_id": analysis.id},
        ip_address=request.client.host if request.client else None,
    )

    return analysis


@router.get("/{contract_id}/results", response_model=FullAnalysisResponse)
async def get_analysis_results(
    contract_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user_contract(contract_id, user, db)

    # Get latest analysis
    result = await db.execute(
        select(Analysis)
        .where(Analysis.contract_id == contract_id)
        .order_by(Analysis.version.desc())
        .limit(1)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise NotFoundError("Analysis")

    # Get related data
    clauses = (await db.execute(
        select(Clause).where(Clause.contract_id == contract_id).order_by(Clause.clause_index)
    )).scalars().all()

    entities = (await db.execute(
        select(Entity).where(Entity.contract_id == contract_id)
    )).scalars().all()

    risks = (await db.execute(
        select(RiskScore).where(RiskScore.contract_id == contract_id).order_by(RiskScore.score.desc())
    )).scalars().all()

    negotiations = (await db.execute(
        select(NegotiationSuggestion).where(NegotiationSuggestion.contract_id == contract_id).order_by(NegotiationSuggestion.sort_order)
    )).scalars().all()

    return FullAnalysisResponse(
        analysis=analysis,
        clauses=clauses,
        entities=entities,
        risks=risks,
        negotiations=negotiations,
    )


@router.get("/{contract_id}/risks", response_model=list[RiskScoreResponse])
async def get_risks(
    contract_id: str,
    min_score: int = 1,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user_contract(contract_id, user, db)

    result = await db.execute(
        select(RiskScore)
        .where(RiskScore.contract_id == contract_id, RiskScore.score >= min_score)
        .order_by(RiskScore.score.desc())
    )
    return result.scalars().all()


@router.get("/{contract_id}/clauses", response_model=list[ClauseResponse])
async def get_clauses(
    contract_id: str,
    category: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user_contract(contract_id, user, db)

    query = select(Clause).where(Clause.contract_id == contract_id)
    if category:
        query = query.where(Clause.category == category)
    query = query.order_by(Clause.clause_index)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{contract_id}/entities", response_model=list[EntityResponse])
async def get_entities(
    contract_id: str,
    entity_type: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user_contract(contract_id, user, db)

    query = select(Entity).where(Entity.contract_id == contract_id)
    if entity_type:
        query = query.where(Entity.entity_type == entity_type)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{contract_id}/negotiations", response_model=list[NegotiationResponse])
async def get_negotiations(
    contract_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_user_contract(contract_id, user, db)

    result = await db.execute(
        select(NegotiationSuggestion)
        .where(NegotiationSuggestion.contract_id == contract_id)
        .order_by(NegotiationSuggestion.sort_order)
    )
    return result.scalars().all()
