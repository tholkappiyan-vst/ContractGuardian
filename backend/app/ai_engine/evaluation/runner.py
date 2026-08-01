"""Evaluation runner — executes the AI pipeline against a labeled dataset and collects predictions."""
import json
import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.ai_engine.evaluation.dataset import EvaluationDataset, ContractSample, ClauseSample, EntitySpan
from app.ai_engine.evaluation.metrics import (
    clause_classification_metrics,
    entity_extraction_metrics,
    risk_prediction_metrics,
    ClassificationMetrics,
    EntityMetrics,
    RiskMetrics,
)


@dataclass
class EvaluationResult:
    """Complete evaluation result."""
    classification: ClassificationMetrics
    entity: EntityMetrics
    risk: RiskMetrics
    elapsed_seconds: float = 0.0
    dataset_name: str = ""
    total_contracts: int = 0
    total_clauses: int = 0
    errors: list[str] = field(default_factory=list)


class EvaluationRunner:
    """Runs the AI pipeline against labeled data and computes metrics.

    Supports two modes:
    1. Live evaluation: calls the actual AI engine (slow, uses API credits)
    2. Offline evaluation: loads pre-computed predictions from JSON

    Usage:
        runner = EvaluationRunner()

        # Live mode (calls AI engine)
        result = await runner.run_live(dataset)

        # Offline mode (pre-computed predictions)
        result = runner.run_offline(dataset_with_predictions)
    """

    def __init__(self, engine=None):
        self._engine = engine

    def _get_engine(self):
        if self._engine is None:
            from app.ai_engine import ContractAIEngine
            self._engine = ContractAIEngine()
        return self._engine

    # ─────────────────────────────────────────────────────────────────────
    # LIVE EVALUATION
    # ─────────────────────────────────────────────────────────────────────

    async def run_live(
        self,
        dataset: EvaluationDataset,
        max_contracts: int | None = None,
    ) -> EvaluationResult:
        """Run the AI engine on each sample and compare to ground truth.

        This makes actual LLM API calls — use sparingly.
        """
        engine = self._get_engine()
        start = time.time()
        errors = []

        samples = dataset.samples[:max_contracts] if max_contracts else dataset.samples

        for sample in samples:
            try:
                # Run clause extraction + risk analysis
                clauses = await engine.extract_clauses(sample.text)
                risks = await engine.analyze_risks(
                    clauses=clauses,
                    contract_type=sample.contract_type,
                    user_role="the person signing",
                    context=sample.text[:3000],
                )

                # Map predictions back to sample clauses
                self._align_predictions(sample, clauses, risks)

            except Exception as e:
                errors.append(f"Contract {sample.id}: {e}")

        elapsed = time.time() - start
        result = self._compute_metrics(dataset, elapsed, errors)
        return result

    # ─────────────────────────────────────────────────────────────────────
    # OFFLINE EVALUATION
    # ─────────────────────────────────────────────────────────────────────

    def run_offline(self, dataset: EvaluationDataset) -> EvaluationResult:
        """Compute metrics from pre-filled predictions in the dataset.

        Assumes predicted_category, predicted_risk_score, and predicted_entities
        are already populated on each ClauseSample.
        """
        return self._compute_metrics(dataset, elapsed=0.0, errors=[])

    def load_predictions(self, dataset: EvaluationDataset, predictions_path: str | Path) -> EvaluationDataset:
        """Load predictions from a JSON file and attach to dataset.

        Predictions format:
        {
          "predictions": {
            "c1": {"category": "non_compete", "risk_score": 7, "entities": [...]},
            "c2": {"category": "payment", "risk_score": 3, "entities": [...]}
          },
          "contract_risks": {
            "eval_001": {"overall_risk": 65, "dimensions": {"financial": 5.5, ...}}
          }
        }
        """
        with open(predictions_path, "r", encoding="utf-8") as f:
            preds = json.load(f)

        clause_preds = preds.get("predictions", {})
        contract_preds = preds.get("contract_risks", {})

        for sample in dataset.samples:
            if sample.id in contract_preds:
                cp = contract_preds[sample.id]
                sample.predicted_overall_risk = cp.get("overall_risk")
                sample.predicted_risk_dimensions = cp.get("dimensions")

            for clause in sample.clauses:
                if clause.id in clause_preds:
                    pred = clause_preds[clause.id]
                    clause.predicted_category = pred.get("category")
                    clause.predicted_risk_score = pred.get("risk_score")
                    clause.predicted_entities = [
                        EntitySpan(
                            text=e["text"],
                            entity_type=e["type"],
                            start=e.get("start", 0),
                            end=e.get("end", 0),
                        )
                        for e in pred.get("entities", [])
                    ]

        return dataset

    # ─────────────────────────────────────────────────────────────────────
    # INTERNAL
    # ─────────────────────────────────────────────────────────────────────

    def _align_predictions(self, sample: ContractSample, clauses: list[dict], risks: dict) -> None:
        """Align AI output to ground truth clauses using text similarity."""
        clause_risks = risks.get("clause_risks", [])

        for true_clause in sample.clauses:
            # Find best matching predicted clause by text overlap
            best_match = None
            best_overlap = 0

            for pred_clause in clauses:
                pred_text = pred_clause.get("body", pred_clause.get("text", "")).lower()
                true_text = true_clause.text.lower()

                # Simple overlap: shared words ratio
                true_words = set(true_text.split())
                pred_words = set(pred_text.split())
                if not true_words:
                    continue
                overlap = len(true_words & pred_words) / len(true_words)

                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match = pred_clause

            if best_match and best_overlap > 0.5:
                true_clause.predicted_category = best_match.get("category", "other")

                # Find risk score for this clause
                idx = best_match.get("index", -1)
                for risk in clause_risks:
                    if risk.get("clause_index") == idx:
                        true_clause.predicted_risk_score = risk.get("score", 5)
                        break
                else:
                    true_clause.predicted_risk_score = best_match.get("risk_score", 5)

        # Overall risk
        overall = risks.get("overall_risk", {})
        if isinstance(overall, dict):
            sample.predicted_overall_risk = overall.get("score")
        elif isinstance(overall, (int, float)):
            sample.predicted_overall_risk = overall

    def _compute_metrics(
        self,
        dataset: EvaluationDataset,
        elapsed: float,
        errors: list[str],
    ) -> EvaluationResult:
        """Compute all metrics from aligned predictions."""
        # Collect classification data
        y_true_cat = []
        y_pred_cat = []
        # Entity data
        true_entities_all = []
        pred_entities_all = []
        # Risk data
        y_true_risk = []
        y_pred_risk = []
        # Overall risk
        y_true_overall = []
        y_pred_overall = []
        # Per-dimension
        dim_true: dict[str, list[float]] = {}
        dim_pred: dict[str, list[float]] = {}

        for sample in dataset.samples:
            # Overall risk
            if sample.predicted_overall_risk is not None:
                y_true_overall.append(sample.true_overall_risk)
                y_pred_overall.append(sample.predicted_overall_risk)

            # Per-dimension
            if sample.predicted_risk_dimensions:
                for dim, val in sample.true_risk_dimensions.items():
                    if dim in sample.predicted_risk_dimensions:
                        dim_true.setdefault(dim, []).append(val)
                        dim_pred.setdefault(dim, []).append(sample.predicted_risk_dimensions[dim])

            for clause in sample.clauses:
                # Classification
                if clause.predicted_category is not None:
                    y_true_cat.append(clause.true_category)
                    y_pred_cat.append(clause.predicted_category)

                # Risk score
                if clause.predicted_risk_score is not None:
                    y_true_risk.append(clause.true_risk_score)
                    y_pred_risk.append(clause.predicted_risk_score)

                # Entities
                if clause.predicted_entities is not None:
                    true_entities_all.append(clause.entities)
                    pred_entities_all.append(clause.predicted_entities)

        # Compute metrics
        classification = clause_classification_metrics(y_true_cat, y_pred_cat) if y_true_cat else ClassificationMetrics(
            accuracy=0, macro_precision=0, macro_recall=0, macro_f1=0, weighted_f1=0, total_samples=0)

        entity = entity_extraction_metrics(true_entities_all, pred_entities_all) if true_entities_all else EntityMetrics(
            entity_accuracy=0, precision=0, recall=0, f1=0, total_true=0, total_pred=0)

        # Combine clause-level and overall risk scores
        all_risk_true = y_true_risk + y_true_overall
        all_risk_pred = y_pred_risk + y_pred_overall

        risk = risk_prediction_metrics(
            all_risk_true, all_risk_pred,
            dimension_true=dim_true, dimension_pred=dim_pred,
        ) if all_risk_true else RiskMetrics(
            mae=0, rmse=0, pearson_correlation=0, spearman_correlation=0,
            within_1_pct=0, within_2_pct=0, total_samples=0)

        return EvaluationResult(
            classification=classification,
            entity=entity,
            risk=risk,
            elapsed_seconds=round(elapsed, 2),
            dataset_name=dataset.name,
            total_contracts=len(dataset.samples),
            total_clauses=dataset.total_clauses,
            errors=errors,
        )
