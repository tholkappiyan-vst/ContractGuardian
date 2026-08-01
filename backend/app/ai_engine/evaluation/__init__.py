"""ML Evaluation Framework for ContractAI Guardian.

Measures performance of:
- Clause classification (accuracy, precision, recall, F1)
- Entity extraction (entity accuracy, F1)
- Risk prediction (MAE, correlation)

Generates performance reports and visualization charts.
"""
from app.ai_engine.evaluation.metrics import (
    clause_classification_metrics,
    entity_extraction_metrics,
    risk_prediction_metrics,
)
from app.ai_engine.evaluation.runner import EvaluationRunner
from app.ai_engine.evaluation.report import ReportGenerator

__all__ = [
    "clause_classification_metrics",
    "entity_extraction_metrics",
    "risk_prediction_metrics",
    "EvaluationRunner",
    "ReportGenerator",
]
