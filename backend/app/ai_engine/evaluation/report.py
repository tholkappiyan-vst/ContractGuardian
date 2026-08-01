"""Report generation — text + JSON summaries of evaluation results."""
import json
from datetime import datetime
from pathlib import Path

from app.ai_engine.evaluation.runner import EvaluationResult


class ReportGenerator:
    """Generates evaluation reports in multiple formats."""

    def to_dict(self, result: EvaluationResult) -> dict:
        """Convert evaluation result to a serializable dict."""
        return {
            "meta": {
                "dataset": result.dataset_name,
                "timestamp": datetime.now().isoformat(),
                "total_contracts": result.total_contracts,
                "total_clauses": result.total_clauses,
                "elapsed_seconds": result.elapsed_seconds,
                "errors": len(result.errors),
            },
            "clause_classification": {
                "accuracy": result.classification.accuracy,
                "macro_precision": result.classification.macro_precision,
                "macro_recall": result.classification.macro_recall,
                "macro_f1": result.classification.macro_f1,
                "weighted_f1": result.classification.weighted_f1,
                "total_samples": result.classification.total_samples,
                "per_class": result.classification.per_class,
            },
            "entity_extraction": {
                "entity_accuracy": result.entity.entity_accuracy,
                "precision": result.entity.precision,
                "recall": result.entity.recall,
                "f1": result.entity.f1,
                "partial_match_f1": result.entity.partial_match_f1,
                "total_true": result.entity.total_true,
                "total_pred": result.entity.total_pred,
                "per_type": result.entity.per_type,
            },
            "risk_prediction": {
                "mae": result.risk.mae,
                "rmse": result.risk.rmse,
                "pearson_correlation": result.risk.pearson_correlation,
                "spearman_correlation": result.risk.spearman_correlation,
                "within_1_point": result.risk.within_1_pct,
                "within_2_points": result.risk.within_2_pct,
                "total_samples": result.risk.total_samples,
                "score_distribution": result.risk.score_distribution,
                "per_dimension": result.risk.per_dimension,
            },
        }

    def to_json(self, result: EvaluationResult, path: str | Path | None = None) -> str:
        """Generate JSON report."""
        report = json.dumps(self.to_dict(result), indent=2)
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(report, encoding="utf-8")
        return report

    def to_text(self, result: EvaluationResult) -> str:
        """Generate human-readable text report."""
        lines = []
        w = lines.append

        w("=" * 70)
        w("  CONTRACTAI GUARDIAN — ML EVALUATION REPORT")
        w("=" * 70)
        w(f"  Dataset: {result.dataset_name}")
        w(f"  Contracts: {result.total_contracts} | Clauses: {result.total_clauses}")
        w(f"  Evaluation time: {result.elapsed_seconds}s")
        if result.errors:
            w(f"  Errors: {len(result.errors)}")
        w("")

        # Classification
        w("-" * 70)
        w("  CLAUSE CLASSIFICATION")
        w("-" * 70)
        c = result.classification
        w(f"  Accuracy:         {c.accuracy:.4f}")
        w(f"  Macro Precision:  {c.macro_precision:.4f}")
        w(f"  Macro Recall:     {c.macro_recall:.4f}")
        w(f"  Macro F1:         {c.macro_f1:.4f}")
        w(f"  Weighted F1:      {c.weighted_f1:.4f}")
        w(f"  Samples:          {c.total_samples}")
        w("")

        if c.per_class:
            w(f"  {'Category':<20} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}")
            w(f"  {'-' * 20} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 10}")
            for cls, metrics in sorted(c.per_class.items()):
                w(f"  {cls:<20} {metrics['precision']:>10.4f} {metrics['recall']:>10.4f} "
                  f"{metrics['f1']:>10.4f} {metrics['support']:>10}")
        w("")

        # Entity Extraction
        w("-" * 70)
        w("  ENTITY EXTRACTION")
        w("-" * 70)
        e = result.entity
        w(f"  Entity Accuracy:  {e.entity_accuracy:.4f}")
        w(f"  Precision:        {e.precision:.4f}")
        w(f"  Recall:           {e.recall:.4f}")
        w(f"  F1:               {e.f1:.4f}")
        w(f"  Partial Match F1: {e.partial_match_f1:.4f}")
        w(f"  True entities:    {e.total_true}")
        w(f"  Pred entities:    {e.total_pred}")
        w("")

        if e.per_type:
            w(f"  {'Entity Type':<20} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}")
            w(f"  {'-' * 20} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 10}")
            for etype, metrics in sorted(e.per_type.items()):
                w(f"  {etype:<20} {metrics['precision']:>10.4f} {metrics['recall']:>10.4f} "
                  f"{metrics['f1']:>10.4f} {metrics['support']:>10}")
        w("")

        # Risk Prediction
        w("-" * 70)
        w("  RISK PREDICTION")
        w("-" * 70)
        r = result.risk
        w(f"  MAE:              {r.mae:.4f}")
        w(f"  RMSE:             {r.rmse:.4f}")
        w(f"  Pearson r:        {r.pearson_correlation:.4f}")
        w(f"  Spearman rho:     {r.spearman_correlation:.4f}")
        w(f"  Within 1 point:   {r.within_1_pct:.1%}")
        w(f"  Within 2 points:  {r.within_2_pct:.1%}")
        w(f"  Samples:          {r.total_samples}")
        w("")

        if r.per_dimension:
            w(f"  {'Dimension':<15} {'MAE':>8} {'Correlation':>13} {'Samples':>10}")
            w(f"  {'-' * 15} {'-' * 8} {'-' * 13} {'-' * 10}")
            for dim, metrics in sorted(r.per_dimension.items()):
                w(f"  {dim:<15} {metrics['mae']:>8.4f} {metrics['correlation']:>13.4f} {metrics['samples']:>10}")
        w("")

        if r.score_distribution:
            w("  Error Distribution:")
            total = sum(r.score_distribution.values())
            for bucket, count in r.score_distribution.items():
                bar = "#" * int((count / max(total, 1)) * 30)
                w(f"    Error {bucket:>3}: {bar} ({count})")
        w("")

        w("=" * 70)
        return "\n".join(lines)

    def save_report(self, result: EvaluationResult, output_dir: str | Path) -> dict[str, str]:
        """Save both JSON and text reports to a directory."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        json_path = output_dir / f"eval_report_{timestamp}.json"
        text_path = output_dir / f"eval_report_{timestamp}.txt"

        self.to_json(result, json_path)
        text_path.write_text(self.to_text(result), encoding="utf-8")

        return {"json": str(json_path), "text": str(text_path)}
