"""API routes for Explainable AI — local and global explanations."""
from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.exceptions import NotFoundError, ForbiddenError
from app.models.user import User
from app.models.contract import Contract
from app.models.analysis import Clause, RiskScore, Analysis
from app.ai_engine.explainability import ExplainabilityEngine
from app.ai_engine.risk_scoring import score_from_ai_output

router = APIRouter()


def _get_explainability_engine() -> ExplainabilityEngine:
    return ExplainabilityEngine()


# ─────────────────────────────────────────────────────────────────────────────
# LOCAL: Explain a single clause
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{contract_id}/clause/{clause_id}")
async def explain_clause(
    contract_id: str,
    clause_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full explainability report for a single clause.

    Returns SHAP word attributions, LIME risk factors, and LLM reasoning.
    """
    contract = await db.get(Contract, contract_id)
    if not contract or contract.deleted_at:
        raise NotFoundError("Contract")
    if contract.user_id != user.id:
        raise ForbiddenError()

    clause = await db.get(Clause, clause_id)
    if not clause or clause.analysis_id is None:
        raise NotFoundError("Clause")

    # Get risk score for this clause
    risk_result = await db.execute(
        select(RiskScore).where(RiskScore.clause_id == clause_id).limit(1)
    )
    risk_row = risk_result.scalar_one_or_none()
    risk_score = risk_row.score if risk_row else 5

    engine = _get_explainability_engine()
    explanation = await engine.explain_clause(
        clause_id=clause_id,
        clause_text=clause.body,
        category=clause.category,
        risk_score=risk_score,
        contract_type=contract.contract_type or "general",
        user_role="the person signing",
    )

    return {
        "clause_id": explanation.clause_id,
        "risk_score": explanation.risk_score,
        "why_risky": explanation.why_risky,
        "reasoning_chain": explanation.reasoning_chain,
        "important_words": explanation.important_words,
        "risk_factors": [
            {
                "factor": f.factor,
                "weight": f.weight,
                "evidence": f.evidence,
                "dimension": f.dimension,
            }
            for f in explanation.risk_factors
        ],
        "word_attributions": [
            {"word": a.word, "score": a.attribution_score}
            for a in explanation.word_attributions
            if abs(a.attribution_score) > 0.1
        ],
        "confidence": explanation.confidence,
    }


# ─────────────────────────────────────────────────────────────────────────────
# LOCAL FAST: Sync explanation without LLM (for tooltips)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{contract_id}/clause/{clause_id}/quick")
async def explain_clause_quick(
    contract_id: str,
    clause_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fast local explanation (SHAP + LIME only, no LLM call).

    Use this for real-time UI tooltips where latency matters.
    """
    contract = await db.get(Contract, contract_id)
    if not contract or contract.deleted_at:
        raise NotFoundError("Contract")
    if contract.user_id != user.id:
        raise ForbiddenError()

    clause = await db.get(Clause, clause_id)
    if not clause:
        raise NotFoundError("Clause")

    risk_result = await db.execute(
        select(RiskScore).where(RiskScore.clause_id == clause_id).limit(1)
    )
    risk_row = risk_result.scalar_one_or_none()
    risk_score = risk_row.score if risk_row else 5

    engine = _get_explainability_engine()
    return engine.explain_clause_sync(
        clause_text=clause.body,
        category=clause.category,
        risk_score=risk_score,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL: Full contract explanation
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{contract_id}/global")
async def explain_contract(
    contract_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full global explainability report for a contract.

    Returns overall risk reasoning, dimension breakdown, main concerns,
    recommendation, and global feature importance.
    """
    contract = await db.get(Contract, contract_id)
    if not contract or contract.deleted_at:
        raise NotFoundError("Contract")
    if contract.user_id != user.id:
        raise ForbiddenError()

    # Get the latest analysis
    analysis_result = await db.execute(
        select(Analysis)
        .where(Analysis.contract_id == contract_id)
        .order_by(Analysis.version.desc())
        .limit(1)
    )
    analysis = analysis_result.scalar_one_or_none()
    if not analysis:
        raise NotFoundError("Analysis")

    # Get all clauses with their risk scores
    clauses_result = await db.execute(
        select(Clause).where(Clause.analysis_id == analysis.id)
    )
    clauses = clauses_result.scalars().all()

    risks_result = await db.execute(
        select(RiskScore).where(RiskScore.analysis_id == analysis.id)
    )
    risks = risks_result.scalars().all()

    # Build clause risk dicts for the engine
    clause_risk_map = {r.clause_id: r for r in risks if r.clause_id}
    clause_risks = []
    for c in clauses:
        risk = clause_risk_map.get(c.id)
        clause_risks.append({
            "clause_id": c.id,
            "clause_index": c.clause_index,
            "body": c.body,
            "text": c.body,
            "category": c.category,
            "title": c.title or "",
            "score": risk.score if risk else 5,
            "risk_score": risk.score if risk else 5,
        })

    if not clause_risks:
        return {
            "overall_score": 0,
            "risk_level": "low",
            "main_concerns": [],
            "dimension_breakdown": [],
            "recommendation": "No clauses found to analyze.",
            "action_items": [],
            "reasoning_chain": [],
            "top_risk_drivers": [],
            "global_feature_importance": [],
            "clause_explanations": [],
            "metadata": {"clauses_explained": 0, "total_clauses": 0},
        }

    # Get scoring result
    ai_risks = [
        {"clause_id": cr["clause_id"], "score": cr["score"], "category": cr["category"]}
        for cr in clause_risks
    ]
    scoring_result = score_from_ai_output(ai_risks)

    # Run explainability engine (limit LLM calls to avoid timeout)
    engine = _get_explainability_engine()
    result = await engine.explain_contract(
        clause_risks=clause_risks,
        scoring_result=scoring_result,
        contract_type=contract.contract_type or "general",
        user_role="the person signing",
        max_clauses=3,
    )

    global_exp = result.global_explanation
    return {
        "overall_score": global_exp.overall_score,
        "risk_level": global_exp.risk_level,
        "main_concerns": global_exp.main_concerns,
        "dimension_breakdown": global_exp.dimension_breakdown,
        "recommendation": global_exp.recommendation,
        "action_items": global_exp.action_items,
        "reasoning_chain": global_exp.reasoning_chain,
        "top_risk_drivers": global_exp.top_risk_drivers,
        "global_feature_importance": global_exp.global_feature_importance,
        "clause_explanations": [
            {
                "clause_id": ce.clause_id,
                "risk_score": ce.risk_score,
                "why_risky": ce.why_risky,
                "important_words": ce.important_words[:8],
                "top_risk_factor": ce.risk_factors[0].factor if ce.risk_factors else None,
            }
            for ce in result.clause_explanations
        ],
        "metadata": result.metadata,
    }


# ─────────────────────────────────────────────────────────────────────────────
# BATCH: Explain multiple clauses at once
# ─────────────────────────────────────────────────────────────────────────────

class BatchExplainRequest(BaseModel):
    clause_ids: list[str]


@router.post("/{contract_id}/batch")
async def explain_clauses_batch(
    contract_id: str,
    body: BatchExplainRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Explain multiple clauses in one request (fast, SHAP+LIME only)."""
    contract = await db.get(Contract, contract_id)
    if not contract or contract.deleted_at:
        raise NotFoundError("Contract")
    if contract.user_id != user.id:
        raise ForbiddenError()

    engine = _get_explainability_engine()
    results = []

    for clause_id in body.clause_ids[:20]:  # cap at 20
        clause = await db.get(Clause, clause_id)
        if not clause:
            continue

        risk_result = await db.execute(
            select(RiskScore).where(RiskScore.clause_id == clause_id).limit(1)
        )
        risk_row = risk_result.scalar_one_or_none()
        risk_score = risk_row.score if risk_row else 5

        explanation = engine.explain_clause_sync(
            clause_text=clause.body,
            category=clause.category,
            risk_score=risk_score,
        )
        explanation["clause_id"] = clause_id
        results.append(explanation)

    return {"explanations": results}
