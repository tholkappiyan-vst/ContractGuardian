"""Visualization charts for evaluation results.

Generates matplotlib charts saved as PNG files:
- Confusion matrix heatmap
- Per-class F1 bar chart
- Risk prediction scatter plot
- Error distribution histogram
- Dimension comparison radar/bar chart
- Entity type performance bars
"""
from pathlib import Path

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from app.ai_engine.evaluation.runner import EvaluationResult


class ChartGenerator:
    """Generates visualization charts from evaluation results."""

    def __init__(self, output_dir: str | Path = "./data/eval_charts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if not HAS_MATPLOTLIB:
            raise ImportError("matplotlib is required for chart generation. Install with: pip install matplotlib")

    def generate_all(self, result: EvaluationResult) -> list[str]:
        """Generate all available charts. Returns list of saved file paths."""
        paths = []

        if result.classification.total_samples > 0:
            paths.append(self.confusion_matrix(result))
            paths.append(self.per_class_f1(result))

        if result.entity.total_true > 0:
            paths.append(self.entity_type_performance(result))

        if result.risk.total_samples > 0:
            paths.append(self.risk_scatter(result))
            paths.append(self.error_distribution(result))

        if result.risk.per_dimension:
            paths.append(self.dimension_comparison(result))

        paths.append(self.summary_dashboard(result))

        return [p for p in paths if p]

    # ─────────────────────────────────────────────────────────────────────
    # CLAUSE CLASSIFICATION CHARTS
    # ─────────────────────────────────────────────────────────────────────

    def confusion_matrix(self, result: EvaluationResult) -> str:
        """Confusion matrix heatmap."""
        cm = result.classification.confusion_matrix
        if not cm:
            return ""

        labels = sorted(cm.keys())
        n = len(labels)
        matrix = np.zeros((n, n))

        for i, true_label in enumerate(labels):
            for j, pred_label in enumerate(labels):
                matrix[i][j] = cm[true_label].get(pred_label, 0)

        fig, ax = plt.subplots(figsize=(max(8, n * 0.8), max(6, n * 0.7)))

        im = ax.imshow(matrix, interpolation="nearest", cmap="Blues")
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel("Predicted", fontsize=10)
        ax.set_ylabel("True", fontsize=10)
        ax.set_title("Clause Classification — Confusion Matrix", fontsize=12, fontweight="bold")

        # Annotate cells
        for i in range(n):
            for j in range(n):
                val = int(matrix[i][j])
                if val > 0:
                    color = "white" if matrix[i][j] > matrix.max() * 0.6 else "black"
                    ax.text(j, i, str(val), ha="center", va="center", color=color, fontsize=8)

        fig.colorbar(im, ax=ax, shrink=0.8)
        plt.tight_layout()

        path = str(self.output_dir / "confusion_matrix.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    def per_class_f1(self, result: EvaluationResult) -> str:
        """Horizontal bar chart of F1 score per class."""
        per_class = result.classification.per_class
        if not per_class:
            return ""

        # Sort by F1 descending
        sorted_classes = sorted(per_class.items(), key=lambda x: x[1]["f1"], reverse=True)
        labels = [c[0] for c in sorted_classes]
        f1_scores = [c[1]["f1"] for c in sorted_classes]
        precisions = [c[1]["precision"] for c in sorted_classes]
        recalls = [c[1]["recall"] for c in sorted_classes]

        fig, ax = plt.subplots(figsize=(10, max(4, len(labels) * 0.4)))

        y_pos = np.arange(len(labels))
        bar_height = 0.25

        bars1 = ax.barh(y_pos - bar_height, f1_scores, bar_height, label="F1", color="#6366f1")
        bars2 = ax.barh(y_pos, precisions, bar_height, label="Precision", color="#22c55e")
        bars3 = ax.barh(y_pos + bar_height, recalls, bar_height, label="Recall", color="#f59e0b")

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel("Score", fontsize=10)
        ax.set_xlim(0, 1.05)
        ax.set_title("Clause Classification — Per-Class Metrics", fontsize=12, fontweight="bold")
        ax.legend(loc="lower right", fontsize=9)
        ax.axvline(x=result.classification.macro_f1, color="red", linestyle="--", alpha=0.5, label="Macro F1")

        plt.tight_layout()
        path = str(self.output_dir / "per_class_f1.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    # ─────────────────────────────────────────────────────────────────────
    # ENTITY EXTRACTION CHARTS
    # ─────────────────────────────────────────────────────────────────────

    def entity_type_performance(self, result: EvaluationResult) -> str:
        """Bar chart of entity extraction metrics per type."""
        per_type = result.entity.per_type
        if not per_type:
            return ""

        types = sorted(per_type.keys())
        f1s = [per_type[t]["f1"] for t in types]
        precisions = [per_type[t]["precision"] for t in types]
        recalls = [per_type[t]["recall"] for t in types]

        fig, ax = plt.subplots(figsize=(max(8, len(types) * 1.2), 5))

        x = np.arange(len(types))
        width = 0.25

        ax.bar(x - width, precisions, width, label="Precision", color="#22c55e")
        ax.bar(x, recalls, width, label="Recall", color="#f59e0b")
        ax.bar(x + width, f1s, width, label="F1", color="#6366f1")

        ax.set_xticks(x)
        ax.set_xticklabels(types, rotation=30, ha="right", fontsize=9)
        ax.set_ylabel("Score", fontsize=10)
        ax.set_ylim(0, 1.1)
        ax.set_title("Entity Extraction — Per-Type Performance", fontsize=12, fontweight="bold")
        ax.legend(fontsize=9)

        # Overall F1 line
        ax.axhline(y=result.entity.f1, color="red", linestyle="--", alpha=0.5)
        ax.annotate(f"Overall F1: {result.entity.f1:.3f}", xy=(len(types) - 1, result.entity.f1 + 0.02),
                    fontsize=8, color="red")

        plt.tight_layout()
        path = str(self.output_dir / "entity_performance.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    # ─────────────────────────────────────────────────────────────────────
    # RISK PREDICTION CHARTS
    # ─────────────────────────────────────────────────────────────────────

    def risk_scatter(self, result: EvaluationResult) -> str:
        """Scatter plot of true vs predicted risk scores."""
        # We don't have raw data in the result — generate from distribution info
        # This chart is best used with raw data, so we'll show a placeholder with metrics
        fig, ax = plt.subplots(figsize=(7, 7))

        # Draw perfect prediction line
        ax.plot([0, 10], [0, 10], "k--", alpha=0.3, label="Perfect prediction")
        ax.fill_between([0, 10], [0, 10], [1, 11], alpha=0.05, color="green", label="Within 1 point")
        ax.fill_between([0, 10], [0, 10], [-1, 9], alpha=0.05, color="green")

        # Add metrics as text
        r = result.risk
        metrics_text = (
            f"MAE: {r.mae:.3f}\n"
            f"RMSE: {r.rmse:.3f}\n"
            f"Pearson r: {r.pearson_correlation:.3f}\n"
            f"Spearman rho: {r.spearman_correlation:.3f}\n"
            f"Within 1pt: {r.within_1_pct:.1%}\n"
            f"Within 2pt: {r.within_2_pct:.1%}\n"
            f"N = {r.total_samples}"
        )
        ax.text(0.05, 0.95, metrics_text, transform=ax.transAxes, fontsize=10,
                verticalalignment="top", bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

        ax.set_xlabel("True Risk Score", fontsize=11)
        ax.set_ylabel("Predicted Risk Score", fontsize=11)
        ax.set_title("Risk Prediction — True vs Predicted", fontsize=12, fontweight="bold")
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.set_aspect("equal")
        ax.legend(loc="lower right", fontsize=9)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        path = str(self.output_dir / "risk_scatter.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    def error_distribution(self, result: EvaluationResult) -> str:
        """Histogram of prediction errors."""
        dist = result.risk.score_distribution
        if not dist:
            return ""

        fig, ax = plt.subplots(figsize=(8, 5))

        buckets = list(dist.keys())
        counts = list(dist.values())
        total = sum(counts)

        colors = ["#22c55e", "#84cc16", "#f59e0b", "#f97316", "#ef4444"]
        bars = ax.bar(buckets, counts, color=colors[:len(buckets)], edgecolor="white", linewidth=0.5)

        # Add percentage labels
        for bar, count in zip(bars, counts):
            if count > 0:
                pct = count / total * 100
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                        f"{pct:.0f}%", ha="center", fontsize=9)

        ax.set_xlabel("Absolute Error (points)", fontsize=10)
        ax.set_ylabel("Count", fontsize=10)
        ax.set_title("Risk Prediction — Error Distribution", fontsize=12, fontweight="bold")

        # Add MAE reference line
        ax.axvline(x=result.risk.mae, color="red", linestyle="--", alpha=0.7)
        ax.annotate(f"MAE = {result.risk.mae:.2f}", xy=(result.risk.mae, max(counts) * 0.9),
                    fontsize=9, color="red")

        plt.tight_layout()
        path = str(self.output_dir / "error_distribution.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    def dimension_comparison(self, result: EvaluationResult) -> str:
        """Bar chart comparing MAE and correlation across risk dimensions."""
        per_dim = result.risk.per_dimension
        if not per_dim:
            return ""

        dims = sorted(per_dim.keys())
        maes = [per_dim[d]["mae"] for d in dims]
        corrs = [per_dim[d]["correlation"] for d in dims]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # MAE per dimension
        colors_mae = ["#ef4444" if m > 2 else "#f59e0b" if m > 1 else "#22c55e" for m in maes]
        ax1.barh(dims, maes, color=colors_mae, edgecolor="white")
        ax1.set_xlabel("MAE", fontsize=10)
        ax1.set_title("MAE by Dimension", fontsize=11, fontweight="bold")
        ax1.set_xlim(0, max(maes) * 1.3 if maes else 1)
        for i, v in enumerate(maes):
            ax1.text(v + 0.02, i, f"{v:.3f}", va="center", fontsize=9)

        # Correlation per dimension
        colors_corr = ["#22c55e" if c > 0.7 else "#f59e0b" if c > 0.4 else "#ef4444" for c in corrs]
        ax2.barh(dims, corrs, color=colors_corr, edgecolor="white")
        ax2.set_xlabel("Pearson Correlation", fontsize=10)
        ax2.set_title("Correlation by Dimension", fontsize=11, fontweight="bold")
        ax2.set_xlim(0, 1.1)
        for i, v in enumerate(corrs):
            ax2.text(v + 0.02, i, f"{v:.3f}", va="center", fontsize=9)

        plt.suptitle("Risk Prediction — Per-Dimension Analysis", fontsize=12, fontweight="bold", y=1.02)
        plt.tight_layout()
        path = str(self.output_dir / "dimension_comparison.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    # ─────────────────────────────────────────────────────────────────────
    # SUMMARY DASHBOARD
    # ─────────────────────────────────────────────────────────────────────

    def summary_dashboard(self, result: EvaluationResult) -> str:
        """Single-page dashboard summarizing all metrics."""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle("ContractAI Guardian — Evaluation Dashboard", fontsize=14, fontweight="bold")

        # Top-left: Key metrics table
        ax = axes[0, 0]
        ax.axis("off")
        metrics_data = [
            ["Metric", "Value", "Target"],
            ["Classification Accuracy", f"{result.classification.accuracy:.1%}", "> 85%"],
            ["Classification F1 (macro)", f"{result.classification.macro_f1:.1%}", "> 80%"],
            ["Entity F1", f"{result.entity.f1:.1%}", "> 75%"],
            ["Risk MAE", f"{result.risk.mae:.2f}", "< 1.5"],
            ["Risk Correlation", f"{result.risk.pearson_correlation:.3f}", "> 0.80"],
            ["Within 2 points", f"{result.risk.within_2_pct:.1%}", "> 80%"],
        ]

        table = ax.table(cellText=metrics_data[1:], colLabels=metrics_data[0],
                         loc="center", cellLoc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.2, 1.5)

        # Color cells based on targets
        for i, row in enumerate(metrics_data[1:], 1):
            # Simple pass/fail coloring
            cell = table[i, 1]
            cell.set_facecolor("#dcfce7" if i < 4 and float(row[1].rstrip("%")) > 75 else "#fef3c7")

        ax.set_title("Key Metrics Summary", fontsize=11, fontweight="bold", pad=20)

        # Top-right: Classification F1 bars
        ax = axes[0, 1]
        if result.classification.per_class:
            classes = sorted(result.classification.per_class.keys())[:10]  # top 10
            f1s = [result.classification.per_class[c]["f1"] for c in classes]
            colors = ["#22c55e" if f > 0.8 else "#f59e0b" if f > 0.5 else "#ef4444" for f in f1s]
            ax.barh(classes, f1s, color=colors)
            ax.set_xlim(0, 1.05)
            ax.set_xlabel("F1 Score")
        ax.set_title("Classification F1 by Category", fontsize=11, fontweight="bold")

        # Bottom-left: Entity metrics
        ax = axes[1, 0]
        if result.entity.per_type:
            types = sorted(result.entity.per_type.keys())[:8]
            f1s = [result.entity.per_type[t]["f1"] for t in types]
            ax.bar(types, f1s, color="#6366f1")
            ax.set_ylim(0, 1.1)
            ax.set_ylabel("F1 Score")
            ax.set_xticklabels(types, rotation=30, ha="right", fontsize=8)
        else:
            ax.text(0.5, 0.5, "No entity data", ha="center", va="center", fontsize=12, color="gray")
        ax.set_title("Entity Extraction by Type", fontsize=11, fontweight="bold")

        # Bottom-right: Risk error distribution
        ax = axes[1, 1]
        if result.risk.score_distribution:
            buckets = list(result.risk.score_distribution.keys())
            counts = list(result.risk.score_distribution.values())
            colors = ["#22c55e", "#84cc16", "#f59e0b", "#f97316", "#ef4444"]
            ax.bar(buckets, counts, color=colors[:len(buckets)])
            ax.set_xlabel("Error (points)")
            ax.set_ylabel("Count")
        else:
            ax.text(0.5, 0.5, "No risk data", ha="center", va="center", fontsize=12, color="gray")
        ax.set_title("Risk Prediction Errors", fontsize=11, fontweight="bold")

        plt.tight_layout()
        path = str(self.output_dir / "summary_dashboard.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path
