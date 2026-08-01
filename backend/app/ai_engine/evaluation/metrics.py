"""Core metrics computation for clause classification, entity extraction, and risk prediction."""
from dataclasses import dataclass, field
from collections import defaultdict

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# CLAUSE CLASSIFICATION METRICS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ClassificationMetrics:
    """Per-class and aggregate classification metrics."""
    accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    weighted_f1: float
    per_class: dict[str, dict[str, float]] = field(default_factory=dict)
    confusion_matrix: dict[str, dict[str, int]] = field(default_factory=dict)
    support: dict[str, int] = field(default_factory=dict)
    total_samples: int = 0


def clause_classification_metrics(
    y_true: list[str],
    y_pred: list[str],
    labels: list[str] | None = None,
) -> ClassificationMetrics:
    """Compute classification metrics for clause category predictions.

    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        labels: Optional ordered label list (auto-detected if None)

    Returns:
        ClassificationMetrics with per-class and aggregate scores
    """
    assert len(y_true) == len(y_pred), "y_true and y_pred must have same length"

    if labels is None:
        labels = sorted(set(y_true) | set(y_pred))

    n = len(y_true)

    # Build confusion matrix
    cm: dict[str, dict[str, int]] = {label: {l: 0 for l in labels} for label in labels}
    for true, pred in zip(y_true, y_pred):
        if true in cm and pred in cm[true]:
            cm[true][pred] += 1

    # Per-class metrics
    per_class = {}
    support = {}
    precisions = []
    recalls = []
    f1s = []
    weights = []

    for label in labels:
        tp = cm[label][label]
        fp = sum(cm[other][label] for other in labels if other != label)
        fn = sum(cm[label][other] for other in labels if other != label)
        total = tp + fn  # support for this class

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": total,
        }
        support[label] = total

        if total > 0:
            precisions.append(precision)
            recalls.append(recall)
            f1s.append(f1)
            weights.append(total)

    # Aggregate metrics
    accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / n if n > 0 else 0.0
    macro_precision = float(np.mean(precisions)) if precisions else 0.0
    macro_recall = float(np.mean(recalls)) if recalls else 0.0
    macro_f1 = float(np.mean(f1s)) if f1s else 0.0

    total_weight = sum(weights)
    weighted_f1 = sum(f * w for f, w in zip(f1s, weights)) / total_weight if total_weight > 0 else 0.0

    return ClassificationMetrics(
        accuracy=round(accuracy, 4),
        macro_precision=round(macro_precision, 4),
        macro_recall=round(macro_recall, 4),
        macro_f1=round(macro_f1, 4),
        weighted_f1=round(weighted_f1, 4),
        per_class=per_class,
        confusion_matrix=cm,
        support=support,
        total_samples=n,
    )


# ─────────────────────────────────────────────────────────────────────────────
# ENTITY EXTRACTION METRICS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EntityMetrics:
    """Entity extraction evaluation metrics."""
    entity_accuracy: float  # exact match accuracy
    precision: float
    recall: float
    f1: float
    per_type: dict[str, dict[str, float]] = field(default_factory=dict)
    partial_match_f1: float = 0.0
    total_true: int = 0
    total_pred: int = 0


@dataclass
class EntitySpan:
    """A single entity annotation."""
    text: str
    entity_type: str
    start: int = 0
    end: int = 0


def entity_extraction_metrics(
    true_entities: list[list[EntitySpan]],
    pred_entities: list[list[EntitySpan]],
    match_mode: str = "exact",
) -> EntityMetrics:
    """Compute entity extraction metrics across documents.

    Args:
        true_entities: Ground truth entities per document
        pred_entities: Predicted entities per document
        match_mode: "exact" (text+type match) or "partial" (type match + text overlap)

    Returns:
        EntityMetrics with per-type breakdown
    """
    assert len(true_entities) == len(pred_entities)

    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_exact_match = 0
    total_true_count = 0
    type_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    partial_tp = 0

    for doc_true, doc_pred in zip(true_entities, pred_entities):
        # Build sets for matching
        true_set = {(e.text.lower().strip(), e.entity_type) for e in doc_true}
        pred_set = {(e.text.lower().strip(), e.entity_type) for e in doc_pred}

        # Exact matches
        matches = true_set & pred_set
        total_tp += len(matches)
        total_fp += len(pred_set - true_set)
        total_fn += len(true_set - pred_set)

        total_exact_match += len(matches)
        total_true_count += len(true_set)

        # Per-type accounting
        for text, etype in matches:
            type_stats[etype]["tp"] += 1
        for text, etype in (pred_set - true_set):
            type_stats[etype]["fp"] += 1
        for text, etype in (true_set - pred_set):
            type_stats[etype]["fn"] += 1

        # Partial matching (type matches and text overlaps)
        if match_mode == "partial":
            for pred_e in doc_pred:
                for true_e in doc_true:
                    if pred_e.entity_type == true_e.entity_type:
                        pred_text = pred_e.text.lower().strip()
                        true_text = true_e.text.lower().strip()
                        if pred_text in true_text or true_text in pred_text:
                            partial_tp += 1
                            break

    # Aggregate metrics
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    entity_accuracy = total_exact_match / total_true_count if total_true_count > 0 else 0.0

    # Partial match F1
    partial_precision = partial_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    partial_recall = partial_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    partial_f1 = 2 * partial_precision * partial_recall / (partial_precision + partial_recall) if (partial_precision + partial_recall) > 0 else 0.0

    # Per-type metrics
    per_type = {}
    for etype, stats in type_stats.items():
        tp, fp, fn = stats["tp"], stats["fp"], stats["fn"]
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        per_type[etype] = {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4), "support": tp + fn}

    return EntityMetrics(
        entity_accuracy=round(entity_accuracy, 4),
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        per_type=per_type,
        partial_match_f1=round(partial_f1, 4),
        total_true=total_true_count,
        total_pred=total_tp + total_fp,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RISK PREDICTION METRICS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RiskMetrics:
    """Risk score prediction metrics."""
    mae: float                  # Mean Absolute Error
    rmse: float                 # Root Mean Squared Error
    pearson_correlation: float  # Pearson correlation coefficient
    spearman_correlation: float # Spearman rank correlation
    within_1_pct: float         # % predictions within 1 point
    within_2_pct: float         # % predictions within 2 points
    per_dimension: dict[str, dict[str, float]] = field(default_factory=dict)
    score_distribution: dict[str, int] = field(default_factory=dict)
    total_samples: int = 0


def risk_prediction_metrics(
    y_true: list[float],
    y_pred: list[float],
    dimensions: list[str] | None = None,
    dimension_true: dict[str, list[float]] | None = None,
    dimension_pred: dict[str, list[float]] | None = None,
) -> RiskMetrics:
    """Compute risk prediction metrics.

    Args:
        y_true: Ground truth risk scores (0-10 or 0-100)
        y_pred: Predicted risk scores
        dimensions: Optional list of dimension names for per-dimension eval
        dimension_true: Per-dimension ground truth scores
        dimension_pred: Per-dimension predicted scores

    Returns:
        RiskMetrics with MAE, correlation, and per-dimension breakdown
    """
    assert len(y_true) == len(y_pred)
    n = len(y_true)
    if n == 0:
        return RiskMetrics(mae=0, rmse=0, pearson_correlation=0, spearman_correlation=0,
                           within_1_pct=0, within_2_pct=0, total_samples=0)

    true_arr = np.array(y_true, dtype=float)
    pred_arr = np.array(y_pred, dtype=float)

    # MAE and RMSE
    errors = np.abs(true_arr - pred_arr)
    mae = float(np.mean(errors))
    rmse = float(np.sqrt(np.mean((true_arr - pred_arr) ** 2)))

    # Correlation
    pearson = _pearson_correlation(true_arr, pred_arr)
    spearman = _spearman_correlation(true_arr, pred_arr)

    # Within-N accuracy
    within_1 = float(np.mean(errors <= 1.0))
    within_2 = float(np.mean(errors <= 2.0))

    # Score distribution (bucket errors)
    dist = {"0": 0, "1": 0, "2": 0, "3": 0, "4+": 0}
    for e in errors:
        if e < 0.5:
            dist["0"] += 1
        elif e < 1.5:
            dist["1"] += 1
        elif e < 2.5:
            dist["2"] += 1
        elif e < 3.5:
            dist["3"] += 1
        else:
            dist["4+"] += 1

    # Per-dimension metrics
    per_dim = {}
    if dimension_true and dimension_pred:
        for dim in (dimensions or dimension_true.keys()):
            if dim in dimension_true and dim in dimension_pred:
                dt = np.array(dimension_true[dim], dtype=float)
                dp = np.array(dimension_pred[dim], dtype=float)
                if len(dt) > 0:
                    dim_mae = float(np.mean(np.abs(dt - dp)))
                    dim_corr = _pearson_correlation(dt, dp)
                    per_dim[dim] = {"mae": round(dim_mae, 4), "correlation": round(dim_corr, 4), "samples": len(dt)}

    return RiskMetrics(
        mae=round(mae, 4),
        rmse=round(rmse, 4),
        pearson_correlation=round(pearson, 4),
        spearman_correlation=round(spearman, 4),
        within_1_pct=round(within_1, 4),
        within_2_pct=round(within_2, 4),
        per_dimension=per_dim,
        score_distribution=dist,
        total_samples=n,
    )


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _pearson_correlation(x: np.ndarray, y: np.ndarray) -> float:
    """Pearson correlation coefficient."""
    if len(x) < 2:
        return 0.0
    x_mean = x - np.mean(x)
    y_mean = y - np.mean(y)
    num = float(np.sum(x_mean * y_mean))
    denom = float(np.sqrt(np.sum(x_mean**2) * np.sum(y_mean**2)))
    return num / denom if denom > 0 else 0.0


def _spearman_correlation(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman rank correlation."""
    if len(x) < 2:
        return 0.0
    x_ranks = _rank_array(x)
    y_ranks = _rank_array(y)
    return _pearson_correlation(x_ranks, y_ranks)


def _rank_array(arr: np.ndarray) -> np.ndarray:
    """Assign ranks to array values (average rank for ties)."""
    temp = arr.argsort()
    ranks = np.empty_like(temp, dtype=float)
    ranks[temp] = np.arange(len(arr), dtype=float)
    # Handle ties by averaging
    unique_vals = np.unique(arr)
    for val in unique_vals:
        mask = arr == val
        if np.sum(mask) > 1:
            ranks[mask] = np.mean(ranks[mask])
    return ranks
