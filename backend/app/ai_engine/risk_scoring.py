"""Contract Risk Scoring Algorithm.

Converts per-clause AI risk assessments (1-10) into a weighted overall
contract score (0-100) across five risk dimensions.

Formula:
    overall_score = Σ (dimension_weight × dimension_score) × severity_multiplier

Where:
    dimension_score = weighted_avg(clause_scores in dimension, weighted by clause_importance)
    severity_multiplier = 1.0 + (0.1 × compounding_pairs) + critical_penalty

    critical_penalty:
        +0.15 if any clause scores 9-10 (dangerous terms exist regardless of average)

    compounding_pairs:
        count of clause pairs that interact to amplify risk (max contribution: +0.3)
"""
from dataclasses import dataclass, field
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

class RiskDimension(str, Enum):
    FINANCIAL = "financial"
    LIABILITY = "liability"
    TERMINATION = "termination"
    COMPLIANCE = "compliance"
    PRIVACY = "privacy"


# Dimension weights (must sum to 1.0)
DIMENSION_WEIGHTS: dict[RiskDimension, float] = {
    RiskDimension.FINANCIAL: 0.30,
    RiskDimension.LIABILITY: 0.25,
    RiskDimension.TERMINATION: 0.20,
    RiskDimension.COMPLIANCE: 0.15,
    RiskDimension.PRIVACY: 0.10,
}

# Which clause categories map to which risk dimension
CATEGORY_TO_DIMENSION: dict[str, RiskDimension] = {
    "payment": RiskDimension.FINANCIAL,
    "penalties": RiskDimension.FINANCIAL,
    "liability": RiskDimension.LIABILITY,
    "warranty": RiskDimension.LIABILITY,
    "termination": RiskDimension.TERMINATION,
    "non_compete": RiskDimension.TERMINATION,
    "force_majeure": RiskDimension.TERMINATION,
    "dispute_resolution": RiskDimension.COMPLIANCE,
    "governing_law": RiskDimension.COMPLIANCE,
    "assignment": RiskDimension.COMPLIANCE,
    "data_privacy": RiskDimension.PRIVACY,
    "confidentiality": RiskDimension.PRIVACY,
    "ip_rights": RiskDimension.FINANCIAL,
}

# How important each clause category is within its dimension
CATEGORY_IMPORTANCE: dict[str, float] = {
    "payment": 1.0,
    "penalties": 0.9,
    "liability": 1.0,
    "warranty": 0.6,
    "termination": 1.0,
    "non_compete": 0.8,
    "force_majeure": 0.4,
    "dispute_resolution": 0.7,
    "governing_law": 0.5,
    "assignment": 0.4,
    "data_privacy": 1.0,
    "confidentiality": 0.8,
    "ip_rights": 0.9,
}


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ClauseRisk:
    """Risk assessment for a single clause."""
    clause_id: str
    category: str
    score: int              # 1-10 from AI
    title: str = ""
    explanation: str = ""


@dataclass
class CompoundingRisk:
    """Two clauses that amplify each other's risk."""
    clause_ids: tuple[str, str]
    explanation: str = ""


@dataclass
class DimensionResult:
    """Scoring result for one risk dimension."""
    dimension: RiskDimension
    raw_score: float        # 0-10 weighted average
    scaled_score: float     # 0-100
    weight: float
    weighted_contribution: float
    clause_count: int
    top_clause: str | None = None


@dataclass
class RiskScoringResult:
    """Complete scoring output."""
    overall_score: int                          # 0-100
    risk_level: str                             # low / medium / high
    dimensions: list[DimensionResult]
    severity_multiplier: float
    critical_clauses: list[str]                 # clause_ids with score 9-10
    compounding_count: int
    breakdown: dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# SCORING ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def calculate_risk_score(
    clause_risks: list[ClauseRisk],
    compounding_risks: list[CompoundingRisk] | None = None,
) -> RiskScoringResult:
    """Calculate overall contract risk score from clause-level assessments.

    Args:
        clause_risks: List of per-clause risk scores (1-10) with categories
        compounding_risks: Optional pairs of clauses that amplify each other

    Returns:
        RiskScoringResult with overall score 0-100 and breakdown
    """
    if not clause_risks:
        return RiskScoringResult(
            overall_score=0,
            risk_level="low",
            dimensions=[],
            severity_multiplier=1.0,
            critical_clauses=[],
            compounding_count=0,
        )

    compounding_risks = compounding_risks or []

    # ─── Step 1: Group clauses by dimension ───────────────────────────────

    dimension_clauses: dict[RiskDimension, list[ClauseRisk]] = {d: [] for d in RiskDimension}

    for clause in clause_risks:
        dimension = CATEGORY_TO_DIMENSION.get(clause.category)
        if dimension:
            dimension_clauses[dimension].append(clause)
        else:
            # Unknown category → split contribution across liability + compliance
            dimension_clauses[RiskDimension.LIABILITY].append(clause)

    # ─── Step 2: Calculate per-dimension weighted score ───────────────────

    dimension_results: list[DimensionResult] = []

    for dimension, weight in DIMENSION_WEIGHTS.items():
        clauses = dimension_clauses[dimension]

        if not clauses:
            # No clauses in this dimension — treat as neutral (5/10)
            raw_score = 5.0
        else:
            # Weighted average by category importance
            total_weight = 0.0
            weighted_sum = 0.0
            for c in clauses:
                importance = CATEGORY_IMPORTANCE.get(c.category, 0.5)
                weighted_sum += c.score * importance
                total_weight += importance
            raw_score = weighted_sum / total_weight if total_weight > 0 else 5.0

        # Scale 1-10 → 0-100
        scaled = ((raw_score - 1) / 9) * 100
        contribution = weight * scaled

        # Find top risk clause in this dimension
        top_clause = max(clauses, key=lambda c: c.score).clause_id if clauses else None

        dimension_results.append(DimensionResult(
            dimension=dimension,
            raw_score=round(raw_score, 2),
            scaled_score=round(scaled, 1),
            weight=weight,
            weighted_contribution=round(contribution, 1),
            clause_count=len(clauses),
            top_clause=top_clause,
        ))

    # ─── Step 3: Base score (weighted sum of dimensions) ──────────────────

    base_score = sum(d.weighted_contribution for d in dimension_results)

    # ─── Step 4: Severity multiplier ─────────────────────────────────────

    # Critical clause penalty: any clause scoring 9-10 bumps the multiplier
    critical_clauses = [c.clause_id for c in clause_risks if c.score >= 9]
    critical_penalty = 0.15 if critical_clauses else 0.0

    # Compounding risk bonus: interacting clauses amplify risk
    compounding_count = min(len(compounding_risks), 3)  # cap at 3
    compounding_bonus = 0.1 * compounding_count

    severity_multiplier = 1.0 + critical_penalty + compounding_bonus

    # ─── Step 5: Final score ─────────────────────────────────────────────

    final_score = base_score * severity_multiplier
    final_score = int(min(100, max(0, round(final_score))))

    # ─── Step 6: Risk level classification ────────────────────────────────

    if final_score <= 30:
        risk_level = "low"
    elif final_score <= 60:
        risk_level = "medium"
    else:
        risk_level = "high"

    return RiskScoringResult(
        overall_score=final_score,
        risk_level=risk_level,
        dimensions=dimension_results,
        severity_multiplier=round(severity_multiplier, 2),
        critical_clauses=critical_clauses,
        compounding_count=compounding_count,
        breakdown={
            "base_score": round(base_score, 1),
            "critical_penalty_applied": bool(critical_clauses),
            "compounding_pairs": compounding_count,
            "formula": "overall = base_score × severity_multiplier",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE
# ─────────────────────────────────────────────────────────────────────────────

def score_from_ai_output(ai_risks: list[dict], compounding: list[dict] | None = None) -> RiskScoringResult:
    """Convert raw AI JSON output to a scored result.

    Accepts the format produced by the risk analysis chain:
    [{"clause_index": 0, "score": 8, "category": "financial_exposure", ...}]
    """
    # Map AI risk categories back to clause categories
    ai_category_map = {
        "financial_exposure": "payment",
        "restrictive_terms": "non_compete",
        "one_sided_obligations": "liability",
        "missing_protections": "liability",
        "unusual_language": "liability",
        "compliance_risk": "governing_law",
        "operational_risk": "termination",
    }

    clause_risks = []
    for r in ai_risks:
        category = ai_category_map.get(r.get("category", ""), r.get("category", "other"))
        clause_risks.append(ClauseRisk(
            clause_id=str(r.get("clause_index", r.get("clause_id", ""))),
            category=category,
            score=r["score"],
            title=r.get("title", ""),
            explanation=r.get("explanation", ""),
        ))

    compounding_risks = []
    if compounding:
        for c in compounding:
            ids = c.get("clause_indices", c.get("clause_ids", []))
            if len(ids) >= 2:
                compounding_risks.append(CompoundingRisk(
                    clause_ids=(str(ids[0]), str(ids[1])),
                    explanation=c.get("explanation", ""),
                ))

    return calculate_risk_score(clause_risks, compounding_risks)


# ─────────────────────────────────────────────────────────────────────────────
# DEMO / SELF-CHECK
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Example: employment contract with some risky clauses
    clauses = [
        ClauseRisk(clause_id="1", category="payment", score=3, title="Salary Terms"),
        ClauseRisk(clause_id="2", category="payment", score=4, title="Bonus Structure"),
        ClauseRisk(clause_id="3", category="liability", score=9, title="Unlimited Liability"),
        ClauseRisk(clause_id="4", category="non_compete", score=8, title="2-Year Non-Compete"),
        ClauseRisk(clause_id="5", category="termination", score=6, title="Termination for Convenience"),
        ClauseRisk(clause_id="6", category="ip_rights", score=7, title="Broad IP Assignment"),
        ClauseRisk(clause_id="7", category="confidentiality", score=4, title="Standard NDA"),
        ClauseRisk(clause_id="8", category="data_privacy", score=5, title="Data Handling"),
        ClauseRisk(clause_id="9", category="dispute_resolution", score=3, title="Arbitration Clause"),
        ClauseRisk(clause_id="10", category="penalties", score=7, title="Signing Bonus Clawback"),
    ]

    compounding = [
        CompoundingRisk(clause_ids=("3", "6"), explanation="Unlimited liability + broad IP = exposure if IP disputed"),
        CompoundingRisk(clause_ids=("4", "5"), explanation="Non-compete + easy termination = locked out of industry"),
    ]

    result = calculate_risk_score(clauses, compounding)

    print("=" * 60)
    print(f"  OVERALL RISK SCORE: {result.overall_score}/100 [{result.risk_level.upper()}]")
    print("=" * 60)
    print()
    print("  Dimension Breakdown:")
    print("  " + "-" * 56)
    for d in result.dimensions:
        bar = "█" * int(d.scaled_score / 5) + "░" * (20 - int(d.scaled_score / 5))
        print(f"  {d.dimension.value:<12} {bar} {d.scaled_score:5.1f}/100  (weight: {d.weight:.0%}, clauses: {d.clause_count})")
    print()
    print(f"  Base score:           {result.breakdown['base_score']:.1f}")
    print(f"  Severity multiplier:  ×{result.severity_multiplier}")
    print(f"  Critical clauses:     {len(result.critical_clauses)} (IDs: {result.critical_clauses})")
    print(f"  Compounding pairs:    {result.compounding_count}")
    print()
    print(f"  Formula: {result.breakdown['base_score']:.1f} × {result.severity_multiplier} = {result.overall_score}")
    print("=" * 60)
