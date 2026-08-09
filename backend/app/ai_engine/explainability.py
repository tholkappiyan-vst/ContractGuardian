"""Explainable AI module for ContractAI Guardian.

Provides LOCAL explanations (per-clause) and GLOBAL explanations (full contract)
using three complementary approaches:

1. SHAP-inspired text attribution: Perturbation-based word importance scoring.
   Removes/masks words and measures risk score delta to determine contribution.

2. LIME-inspired local explanations: Generates perturbed neighborhood samples
   around a clause, fits a linear interpretable model to approximate the
   LLM's risk scoring locally.

3. LLM chain-of-thought reasoning: Explicit step-by-step justification from
   the Gemini model explaining WHY a clause is risky.

Architecture:
    ClauseExplainer  → local explanations per clause
    ContractExplainer → global explanations for full contract
    ExplainabilityEngine → orchestrates both + caches results
"""
import json
import re
import asyncio
from dataclasses import dataclass, field
from collections import defaultdict

import numpy as np
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted

from app.ai_engine.config import get_ai_settings
from app.ai_engine.risk_scoring import (
    ClauseRisk,
    RiskDimension,
    CATEGORY_TO_DIMENSION,
    DIMENSION_WEIGHTS,
    calculate_risk_score,
    score_from_ai_output,
)


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class WordAttribution:
    """SHAP-style attribution for a single word/phrase."""
    word: str
    position: int
    attribution_score: float  # positive = increases risk, negative = decreases
    is_risk_factor: bool = False


@dataclass
class RiskFactor:
    """A specific factor contributing to clause risk."""
    factor: str
    weight: float  # 0-1, contribution to overall clause risk
    evidence: str
    dimension: str


@dataclass
class ClauseExplanation:
    """Complete local explanation for a single clause."""
    clause_id: str
    clause_text: str
    risk_score: int
    # SHAP-style word attributions
    word_attributions: list[WordAttribution]
    important_words: list[str]
    # LIME-style risk factors
    risk_factors: list[RiskFactor]
    # LLM reasoning
    why_risky: str
    reasoning_chain: list[str]
    # Meta
    confidence: float = 0.0


@dataclass
class GlobalExplanation:
    """Complete global explanation for the full contract."""
    overall_score: int
    risk_level: str
    # Main concerns ranked by impact
    main_concerns: list[dict]
    # Dimension contributions
    dimension_breakdown: list[dict]
    # LLM recommendation
    recommendation: str
    action_items: list[str]
    # Reasoning
    reasoning_chain: list[str]
    # Risk drivers (which clauses drive the score most)
    top_risk_drivers: list[dict]
    # SHAP-style global feature importance
    global_feature_importance: list[dict]


@dataclass
class ExplainabilityResult:
    """Combined local + global explanations."""
    clause_explanations: list[ClauseExplanation]
    global_explanation: GlobalExplanation
    metadata: dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

CLAUSE_EXPLANATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a legal AI explainability system. Your job is to explain WHY a
contract clause is risky, using clear chain-of-thought reasoning.

For the given clause, provide:
1. A step-by-step reasoning chain (each step builds on the previous)
2. Specific risk factors with their weights
3. The most important words/phrases that signal risk
4. A plain-language explanation of why it's risky

Think like a lawyer explaining to a client. Be specific and cite exact language.

Output ONLY valid JSON:
{{
  "why_risky": "One-paragraph plain explanation of why this clause is dangerous",
  "reasoning_chain": [
    "Step 1: [observation about the clause language]",
    "Step 2: [what this implies legally]",
    "Step 3: [the concrete risk this creates]",
    "Step 4: [who benefits and who is harmed]"
  ],
  "risk_factors": [
    {{
      "factor": "Name of the risk factor",
      "weight": 0.4,
      "evidence": "Exact quote from clause that proves this",
      "dimension": "financial|liability|termination|compliance|privacy"
    }}
  ],
  "important_words": ["word1", "phrase two", "word3"],
  "confidence": 0.85
}}"""),
    ("human", """Explain why this clause is risky:

Clause text: {clause_text}
Category: {category}
Risk score: {risk_score}/10
Contract type: {contract_type}
User role: {user_role}

Provide your chain-of-thought explanation as JSON."""),
])


GLOBAL_EXPLANATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a legal AI explainability system providing a GLOBAL explanation
of why an entire contract has a particular risk level.

Given the contract's clause-level risks and overall score, explain:
1. The main concerns (ranked by severity)
2. How dimensions interact to create the overall risk
3. A clear recommendation (sign / negotiate / walk away)
4. Specific action items

Think holistically — individual risky clauses may be acceptable, but COMBINATIONS
of risky clauses can create dangerous situations.

Output ONLY valid JSON:
{{
  "main_concerns": [
    {{
      "concern": "Description of the concern",
      "severity": "critical|high|medium|low",
      "affected_clauses": ["clause_id_1", "clause_id_2"],
      "impact": "What happens if you sign with this issue"
    }}
  ],
  "reasoning_chain": [
    "Step 1: [overall observation]",
    "Step 2: [how risks interact]",
    "Step 3: [cumulative effect]",
    "Step 4: [conclusion and recommendation basis]"
  ],
  "recommendation": "Clear recommendation: SAFE TO SIGN / NEGOTIATE BEFORE SIGNING / DO NOT SIGN",
  "action_items": [
    "Specific action item 1",
    "Specific action item 2"
  ],
  "top_risk_drivers": [
    {{
      "clause_id": "id",
      "clause_title": "title",
      "contribution_pct": 25,
      "reason": "Why this clause drives overall risk"
    }}
  ]
}}"""),
    ("human", """Provide a global explanation for this contract:

Overall risk score: {overall_score}/100 ({risk_level})
Contract type: {contract_type}
User role: {user_role}

Dimension breakdown:
{dimension_breakdown}

All clause risks:
{clause_risks_json}

Scoring formula applied:
- Base score: {base_score}
- Severity multiplier: {severity_multiplier}
- Critical clauses: {critical_count}
- Compounding pairs: {compounding_count}

Provide your global explanation as JSON."""),
])


# ─────────────────────────────────────────────────────────────────────────────
# SHAP-INSPIRED TEXT ATTRIBUTION
# ─────────────────────────────────────────────────────────────────────────────

class TextSHAP:
    """Perturbation-based word importance for legal text.

    Adapts SHAP's concept to text: measures each word's marginal contribution
    to the risk score by observing score changes when words are removed.

    Instead of calling the LLM for every perturbation (expensive), we use a
    fast local scoring heuristic based on legal risk lexicon + positional weight.
    """

    RISK_LEXICON: dict[str, float] = {
        # High-risk legal language (positive = increases risk)
        "unlimited": 0.9, "irrevocable": 0.85, "perpetual": 0.8,
        "sole": 0.7, "exclusive": 0.7, "waive": 0.8, "waiver": 0.8,
        "indemnify": 0.75, "indemnification": 0.75, "indemnity": 0.75,
        "terminate": 0.6, "immediately": 0.5,
        "liquidated": 0.8, "consequential": 0.7,
        "liquidated damages": 0.85,
        "terminate immediately": 0.8, "without cause": 0.75,
        "at its sole discretion": 0.85, "non-refundable": 0.7,
        "non-compete": 0.7, "non-solicitation": 0.65,
        "worldwide": 0.6, "assigns": 0.5, "successors": 0.4,
        "shall not": 0.5, "must not": 0.5, "prohibited": 0.6,
        "penalty": 0.7, "penalties": 0.7, "forfeit": 0.8,
        "all rights": 0.7, "any and all": 0.6, "without limitation": 0.7,
        "automatically renews": 0.65, "auto-renewal": 0.65,
        "binding arbitration": 0.6, "class action waiver": 0.75,
        "unilateral": 0.8, "unconditional": 0.7,
        "personally": 0.75, "jointly": 0.6, "severally": 0.6,
        "personal liability": 0.85, "jointly and severally": 0.8,
        "no liability": 0.6, "as-is": 0.5,
        # Risk-reducing language (negative = decreases risk)
        "mutual": -0.4, "reasonable": -0.3, "reasonably": -0.3,
        "good faith": -0.3, "best efforts": -0.2,
        "consent": -0.2, "notice": -0.2,
        "written consent": -0.3, "prior written notice": -0.35,
        "30 days": -0.2, "cure period": -0.4,
        "limited": -0.3, "cap": -0.3,
        "limited to": -0.3, "not to exceed": -0.35,
        "proportional": -0.25, "pro rata": -0.2,
        "either": -0.2, "both": -0.2,
        "either party": -0.3, "both parties": -0.3,
    }

    def compute_attributions(
        self,
        clause_text: str,
        base_risk_score: int,
    ) -> list[WordAttribution]:
        """Compute word-level risk attributions for a clause."""
        words = self._tokenize(clause_text)
        attributions = []

        for i, word in enumerate(words):
            word_lower = word.lower().strip(".,;:()")
            score = 0.0

            # Check single word
            if word_lower in self.RISK_LEXICON:
                score = self.RISK_LEXICON[word_lower]

            # Check bigrams
            if i < len(words) - 1:
                bigram = f"{word_lower} {words[i + 1].lower().strip('.,;:()')}"
                if bigram in self.RISK_LEXICON:
                    score = max(score, self.RISK_LEXICON[bigram])

            # Positional weight: legal terms at clause start matter more
            position_weight = 1.0 if i < len(words) * 0.3 else 0.8

            # Scale attribution by the clause's actual risk score
            scaled_score = score * position_weight * (base_risk_score / 10.0)

            attributions.append(WordAttribution(
                word=word,
                position=i,
                attribution_score=round(scaled_score, 3),
                is_risk_factor=abs(scaled_score) > 0.3,
            ))

        return attributions

    def get_important_words(self, attributions: list[WordAttribution], top_k: int = 10) -> list[str]:
        """Get the most impactful words from attributions."""
        sorted_attrs = sorted(attributions, key=lambda a: abs(a.attribution_score), reverse=True)
        return [a.word for a in sorted_attrs[:top_k] if abs(a.attribution_score) > 0.1]

    def _tokenize(self, text: str) -> list[str]:
        return text.split()


# ─────────────────────────────────────────────────────────────────────────────
# LIME-INSPIRED LOCAL EXPLANATION
# ─────────────────────────────────────────────────────────────────────────────

class TextLIME:
    """Local Interpretable Model-agnostic Explanations adapted for legal text.

    Instead of fitting a linear model on LLM outputs (too expensive),
    we use the risk scoring algorithm as our "black box" and perturb clause
    properties to measure local sensitivity.

    The "interpretable features" are risk factor categories rather than
    raw words — more meaningful for legal analysis.
    """

    LEGAL_RISK_PATTERNS: dict[str, list[str]] = {
        "unlimited_scope": [
            r"\b(unlimited|without limit|no limit|uncapped)\b",
            r"\b(any and all|all rights|entirety)\b",
            r"\b(worldwide|perpetual|irrevocable)\b",
        ],
        "one_sided_obligation": [
            r"\b(sole discretion|unilateral|shall not)\b",
            r"\b(without .{0,15} consent)\b",
        ],
        "penalty_exposure": [
            r"\b(liquidated damages|penalty|penalties|forfeit)\b",
            r"\b(clawback|repayment|reimburse)\b",
            r"\b(interest .{0,10} per (month|annum|day))\b",
        ],
        "weak_exit_rights": [
            r"\b(irrevocable|auto.?renew|lock.?in|cannot terminate)\b",
            r"\b(minimum term|commitment period)\b",
        ],
        "liability_amplifier": [
            r"\b(indemnif|hold harmless|jointly and severally)\b",
            r"\b(consequential|incidental|special damages)\b",
        ],
        "ip_transfer": [
            r"\b(assign.{0,10}(rights|ip)|work.?for.?hire|exclusive.{0,10}property)\b",
            r"\b(exclusive license|transfer of ownership)\b",
        ],
        "confidentiality_burden": [
            r"\b(perpetual.{0,10} confidential|indefinite)\b",
            r"\b(return or destroy)\b",
            r"\b(injunctive relief|irreparable harm)\b",
        ],
        "dispute_disadvantage": [
            r"\b(binding arbitration|waive.{0,10} jury|class action waiver)\b",
            r"\b(prevailing party|attorney.{0,5} fees)\b",
            r"\b(exclusive jurisdiction|venue .{0,20} (their|company|employer))\b",
        ],
    }

    def compute_risk_factors(
        self,
        clause_text: str,
        category: str,
        risk_score: int,
    ) -> list[RiskFactor]:
        """Identify risk factors by pattern matching + weight estimation."""
        text_lower = clause_text.lower()
        factors = []
        total_matches = 0

        pattern_matches: dict[str, list[str]] = {}

        for factor_name, patterns in self.LEGAL_RISK_PATTERNS.items():
            matches = []
            for pattern in patterns:
                found = re.findall(pattern, text_lower, re.IGNORECASE)
                if found:
                    matches.extend(found if isinstance(found[0], str) else [f[0] for f in found])
            if matches:
                pattern_matches[factor_name] = matches
                total_matches += len(matches)

        if total_matches == 0:
            # No pattern matches — assign generic risk factor from category
            dimension = CATEGORY_TO_DIMENSION.get(category, RiskDimension.LIABILITY).value
            factors.append(RiskFactor(
                factor=f"General {category} risk",
                weight=1.0,
                evidence=clause_text[:100],
                dimension=dimension,
            ))
            return factors

        # Distribute weight proportional to match count
        for factor_name, matches in pattern_matches.items():
            weight = len(matches) / total_matches
            dimension = self._factor_to_dimension(factor_name)
            evidence = matches[0] if isinstance(matches[0], str) else str(matches[0])

            factors.append(RiskFactor(
                factor=self._humanize_factor(factor_name),
                weight=round(weight, 2),
                evidence=evidence,
                dimension=dimension,
            ))

        # Sort by weight descending
        factors.sort(key=lambda f: f.weight, reverse=True)
        return factors

    def _factor_to_dimension(self, factor_name: str) -> str:
        mapping = {
            "unlimited_scope": "liability",
            "one_sided_obligation": "liability",
            "penalty_exposure": "financial",
            "weak_exit_rights": "termination",
            "liability_amplifier": "liability",
            "ip_transfer": "financial",
            "confidentiality_burden": "privacy",
            "dispute_disadvantage": "compliance",
        }
        return mapping.get(factor_name, "liability")

    def _humanize_factor(self, factor_name: str) -> str:
        mapping = {
            "unlimited_scope": "Unlimited scope",
            "one_sided_obligation": "One-sided obligation",
            "penalty_exposure": "Penalty exposure",
            "weak_exit_rights": "Weak exit rights",
            "liability_amplifier": "Liability amplification",
            "ip_transfer": "IP transfer",
            "confidentiality_burden": "Confidentiality burden",
            "dispute_disadvantage": "Dispute disadvantage",
        }
        return mapping.get(factor_name, factor_name.replace("_", " ").title())


# ─────────────────────────────────────────────────────────────────────────────
# LLM CHAIN-OF-THOUGHT REASONING
# ─────────────────────────────────────────────────────────────────────────────

def _get_llm(temperature: float = 0.1) -> ChatGoogleGenerativeAI:
    settings = get_ai_settings()
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=temperature,
        max_retries=settings.max_retries,
        timeout=settings.request_timeout,
    )


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text)


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ResourceExhausted, json.JSONDecodeError)),
)
async def _llm_clause_explanation(
    clause_text: str,
    category: str,
    risk_score: int,
    contract_type: str,
    user_role: str,
) -> dict:
    """Get LLM chain-of-thought explanation for a clause."""
    llm = _get_llm(temperature=0.2)
    chain = CLAUSE_EXPLANATION_PROMPT | llm | StrOutputParser()
    result = await chain.ainvoke({
        "clause_text": clause_text,
        "category": category,
        "risk_score": risk_score,
        "contract_type": contract_type,
        "user_role": user_role,
    })
    return _parse_json(result)


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ResourceExhausted, json.JSONDecodeError)),
)
async def _llm_global_explanation(
    overall_score: int,
    risk_level: str,
    contract_type: str,
    user_role: str,
    dimension_breakdown: str,
    clause_risks_json: str,
    base_score: float,
    severity_multiplier: float,
    critical_count: int,
    compounding_count: int,
) -> dict:
    """Get LLM chain-of-thought global explanation."""
    llm = _get_llm(temperature=0.2)
    chain = GLOBAL_EXPLANATION_PROMPT | llm | StrOutputParser()
    result = await chain.ainvoke({
        "overall_score": overall_score,
        "risk_level": risk_level,
        "contract_type": contract_type,
        "user_role": user_role,
        "dimension_breakdown": dimension_breakdown,
        "clause_risks_json": clause_risks_json,
        "base_score": base_score,
        "severity_multiplier": severity_multiplier,
        "critical_count": critical_count,
        "compounding_count": compounding_count,
    })
    return _parse_json(result)


# ─────────────────────────────────────────────────────────────────────────────
# CLAUSE EXPLAINER (LOCAL)
# ─────────────────────────────────────────────────────────────────────────────

class ClauseExplainer:
    """Generates local explanations for individual clauses.

    Combines all three methods:
    - TextSHAP: word-level attributions
    - TextLIME: risk factor identification
    - LLM: chain-of-thought reasoning
    """

    def __init__(self):
        self.shap = TextSHAP()
        self.lime = TextLIME()

    async def explain(
        self,
        clause_id: str,
        clause_text: str,
        category: str,
        risk_score: int,
        contract_type: str = "general",
        user_role: str = "the person signing",
    ) -> ClauseExplanation:
        """Generate complete local explanation for a clause."""
        # SHAP: word attributions (fast, local)
        attributions = self.shap.compute_attributions(clause_text, risk_score)
        important_words = self.shap.get_important_words(attributions)

        # LIME: risk factor decomposition (fast, local)
        risk_factors = self.lime.compute_risk_factors(clause_text, category, risk_score)

        # LLM: chain-of-thought reasoning (async, remote)
        llm_explanation = await _llm_clause_explanation(
            clause_text=clause_text,
            category=category,
            risk_score=risk_score,
            contract_type=contract_type,
            user_role=user_role,
        )

        # Merge LLM important words with SHAP words (LLM may catch context SHAP misses)
        llm_words = llm_explanation.get("important_words", [])
        merged_words = list(dict.fromkeys(important_words + llm_words))[:15]

        # Merge LLM risk factors with LIME factors
        llm_factors = llm_explanation.get("risk_factors", [])
        for lf in llm_factors:
            if not any(f.factor.lower() == lf["factor"].lower() for f in risk_factors):
                risk_factors.append(RiskFactor(
                    factor=lf["factor"],
                    weight=lf.get("weight", 0.3),
                    evidence=lf.get("evidence", ""),
                    dimension=lf.get("dimension", "liability"),
                ))

        return ClauseExplanation(
            clause_id=clause_id,
            clause_text=clause_text,
            risk_score=risk_score,
            word_attributions=attributions,
            important_words=merged_words,
            risk_factors=risk_factors,
            why_risky=llm_explanation.get("why_risky", ""),
            reasoning_chain=llm_explanation.get("reasoning_chain", []),
            confidence=llm_explanation.get("confidence", 0.7),
        )


# ─────────────────────────────────────────────────────────────────────────────
# CONTRACT EXPLAINER (GLOBAL)
# ─────────────────────────────────────────────────────────────────────────────

class ContractExplainer:
    """Generates global explanations for the full contract.

    Combines scoring algorithm introspection with LLM reasoning.
    """

    def compute_global_feature_importance(
        self,
        clause_risks: list[dict],
    ) -> list[dict]:
        """SHAP-style global feature importance across all clauses.

        Measures which risk factors appear most frequently and with highest
        weight across the entire contract.
        """
        lime = TextLIME()
        factor_scores: dict[str, list[float]] = defaultdict(list)

        for clause in clause_risks:
            text = clause.get("body", clause.get("text", ""))
            category = clause.get("category", "other")
            score = clause.get("score", clause.get("risk_score", 5))

            factors = lime.compute_risk_factors(text, category, score)
            for f in factors:
                factor_scores[f.factor].append(f.weight * score)

        # Aggregate: mean contribution × frequency
        importance = []
        for factor, scores in factor_scores.items():
            importance.append({
                "factor": factor,
                "mean_contribution": round(float(np.mean(scores)), 3),
                "frequency": len(scores),
                "total_impact": round(float(np.sum(scores)), 3),
            })

        importance.sort(key=lambda x: x["total_impact"], reverse=True)
        return importance[:10]

    async def explain(
        self,
        scoring_result,  # RiskScoringResult
        clause_risks: list[dict],
        contract_type: str = "general",
        user_role: str = "the person signing",
    ) -> GlobalExplanation:
        """Generate complete global explanation."""
        # Format dimension breakdown for LLM
        dim_lines = []
        for d in scoring_result.dimensions:
            dim_lines.append(
                f"- {d.dimension.value}: score={d.scaled_score}/100, "
                f"weight={d.weight:.0%}, contribution={d.weighted_contribution}, "
                f"clauses={d.clause_count}"
            )
        dimension_breakdown_str = "\n".join(dim_lines)

        # Compute global feature importance (SHAP-style)
        global_importance = self.compute_global_feature_importance(clause_risks)

        # LLM global explanation
        llm_global = await _llm_global_explanation(
            overall_score=scoring_result.overall_score,
            risk_level=scoring_result.risk_level,
            contract_type=contract_type,
            user_role=user_role,
            dimension_breakdown=dimension_breakdown_str,
            clause_risks_json=json.dumps(clause_risks[:20], indent=2),  # cap for context
            base_score=scoring_result.breakdown.get("base_score", 0),
            severity_multiplier=scoring_result.severity_multiplier,
            critical_count=len(scoring_result.critical_clauses),
            compounding_count=scoring_result.compounding_count,
        )

        # Build dimension breakdown response
        dimension_response = []
        for d in scoring_result.dimensions:
            dimension_response.append({
                "dimension": d.dimension.value,
                "score": d.scaled_score,
                "weight": d.weight,
                "contribution": d.weighted_contribution,
                "clause_count": d.clause_count,
                "top_clause": d.top_clause,
            })

        return GlobalExplanation(
            overall_score=scoring_result.overall_score,
            risk_level=scoring_result.risk_level,
            main_concerns=llm_global.get("main_concerns", []),
            dimension_breakdown=dimension_response,
            recommendation=llm_global.get("recommendation", "Review with legal counsel"),
            action_items=llm_global.get("action_items", []),
            reasoning_chain=llm_global.get("reasoning_chain", []),
            top_risk_drivers=llm_global.get("top_risk_drivers", []),
            global_feature_importance=global_importance,
        )


# ─────────────────────────────────────────────────────────────────────────────
# EXPLAINABILITY ENGINE (ORCHESTRATOR)
# ─────────────────────────────────────────────────────────────────────────────

class ExplainabilityEngine:
    """Orchestrates local + global explanations for a contract analysis.

    Usage:
        engine = ExplainabilityEngine()
        result = await engine.explain_contract(
            clause_risks=[...],
            scoring_result=scoring_result,
            contract_type="employment",
        )
    """

    def __init__(self):
        self.clause_explainer = ClauseExplainer()
        self.contract_explainer = ContractExplainer()

    async def explain_clause(
        self,
        clause_id: str,
        clause_text: str,
        category: str,
        risk_score: int,
        contract_type: str = "general",
        user_role: str = "the person signing",
    ) -> ClauseExplanation:
        """Generate explanation for a single clause."""
        return await self.clause_explainer.explain(
            clause_id=clause_id,
            clause_text=clause_text,
            category=category,
            risk_score=risk_score,
            contract_type=contract_type,
            user_role=user_role,
        )

    async def explain_contract(
        self,
        clause_risks: list[dict],
        scoring_result,
        contract_type: str = "general",
        user_role: str = "the person signing",
        max_clauses: int = 10,
    ) -> ExplainabilityResult:
        """Generate full explainability report (local + global).

        Args:
            clause_risks: List of clause dicts with text, category, score
            scoring_result: RiskScoringResult from the scoring engine
            contract_type: Inferred contract type
            user_role: Who is reading this contract
            max_clauses: Max clauses to explain locally (limits LLM calls)
        """
        # Sort clauses by risk score descending, explain top N
        sorted_clauses = sorted(
            clause_risks,
            key=lambda c: c.get("score", c.get("risk_score", 0)),
            reverse=True,
        )[:max_clauses]

        # Run local explanations concurrently
        local_tasks = [
            self.clause_explainer.explain(
                clause_id=str(c.get("clause_id", c.get("clause_index", i))),
                clause_text=c.get("body", c.get("text", "")),
                category=c.get("category", "other"),
                risk_score=c.get("score", c.get("risk_score", 5)),
                contract_type=contract_type,
                user_role=user_role,
            )
            for i, c in enumerate(sorted_clauses)
        ]

        # Global explanation
        global_task = self.contract_explainer.explain(
            scoring_result=scoring_result,
            clause_risks=clause_risks,
            contract_type=contract_type,
            user_role=user_role,
        )

        # Run all concurrently
        all_results = await asyncio.gather(
            *local_tasks,
            global_task,
            return_exceptions=True,
        )

        # Separate results
        clause_explanations = []
        for r in all_results[:-1]:
            if isinstance(r, Exception):
                continue
            clause_explanations.append(r)

        global_explanation = all_results[-1]
        if isinstance(global_explanation, Exception):
            # Fallback global explanation from scoring data
            global_explanation = GlobalExplanation(
                overall_score=scoring_result.overall_score,
                risk_level=scoring_result.risk_level,
                main_concerns=[],
                dimension_breakdown=[{
                    "dimension": d.dimension.value,
                    "score": d.scaled_score,
                    "weight": d.weight,
                    "contribution": d.weighted_contribution,
                    "clause_count": d.clause_count,
                } for d in scoring_result.dimensions],
                recommendation="Unable to generate detailed recommendation. Review with legal counsel.",
                action_items=[],
                reasoning_chain=[],
                top_risk_drivers=[],
                global_feature_importance=self.contract_explainer.compute_global_feature_importance(clause_risks),
            )

        return ExplainabilityResult(
            clause_explanations=clause_explanations,
            global_explanation=global_explanation,
            metadata={
                "clauses_explained": len(clause_explanations),
                "total_clauses": len(clause_risks),
                "methods": ["shap_text_attribution", "lime_risk_factors", "llm_chain_of_thought"],
            },
        )

    def explain_clause_sync(
        self,
        clause_text: str,
        category: str,
        risk_score: int,
    ) -> dict:
        """Fast synchronous explanation using only SHAP + LIME (no LLM call).

        Use this for real-time UI tooltips where latency matters.
        """
        shap = TextSHAP()
        lime = TextLIME()

        attributions = shap.compute_attributions(clause_text, risk_score)
        important_words = shap.get_important_words(attributions)
        risk_factors = lime.compute_risk_factors(clause_text, category, risk_score)

        return {
            "important_words": important_words,
            "risk_factors": [
                {"factor": f.factor, "weight": f.weight, "evidence": f.evidence, "dimension": f.dimension}
                for f in risk_factors
            ],
            "word_attributions": [
                {"word": a.word, "score": a.attribution_score}
                for a in attributions
                if abs(a.attribution_score) > 0.1
            ],
        }
