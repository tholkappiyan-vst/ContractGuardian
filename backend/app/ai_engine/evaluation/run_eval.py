"""Standalone evaluation script.

Run:
    python -m app.ai_engine.evaluation.run_eval [--live] [--dataset path.json] [--output-dir ./reports]

Modes:
    Default: Runs against sample dataset with simulated predictions (tests the framework)
    --live:  Calls the actual AI engine (requires API keys, costs money)
    --dataset: Path to a custom labeled dataset JSON
"""
import argparse
import asyncio
import sys
from pathlib import Path

from app.ai_engine.evaluation.dataset import (
    EvaluationDataset,
    load_dataset,
    save_dataset,
    create_sample_dataset,
    ClauseSample,
    EntitySpan,
)
from app.ai_engine.evaluation.runner import EvaluationRunner
from app.ai_engine.evaluation.report import ReportGenerator
from app.ai_engine.evaluation.metrics import EntitySpan


def _simulate_predictions(dataset: EvaluationDataset) -> EvaluationDataset:
    """Add simulated predictions for framework testing.

    Simulates an 80-85% accurate model with realistic error patterns:
    - Most predictions correct
    - Some category confusions (e.g., liability <-> warranty)
    - Risk scores within 1-2 points usually
    - Entity extraction misses some partial matches
    """
    import random
    random.seed(42)

    CONFUSION_MAP = {
        "liability": ["warranty", "liability", "liability", "liability", "liability"],
        "warranty": ["liability", "warranty", "warranty", "warranty"],
        "non_compete": ["termination", "non_compete", "non_compete", "non_compete"],
        "payment": ["penalties", "payment", "payment", "payment", "payment"],
        "termination": ["non_compete", "termination", "termination", "termination"],
    }

    for sample in dataset.samples:
        # Overall risk: add noise ±5
        noise = random.gauss(0, 3)
        sample.predicted_overall_risk = max(0, min(100, sample.true_overall_risk + noise))

        # Dimension risks: add noise ±1
        sample.predicted_risk_dimensions = {}
        for dim, val in sample.true_risk_dimensions.items():
            dim_noise = random.gauss(0, 0.8)
            sample.predicted_risk_dimensions[dim] = max(0, min(10, val + dim_noise))

        for clause in sample.clauses:
            # Category: mostly correct, some confusion
            if random.random() < 0.85:
                clause.predicted_category = clause.true_category
            else:
                options = CONFUSION_MAP.get(clause.true_category, [clause.true_category])
                clause.predicted_category = random.choice(options)

            # Risk score: within ±2 usually
            risk_noise = random.gauss(0, 1.2)
            clause.predicted_risk_score = max(1, min(10, round(clause.true_risk_score + risk_noise)))

            # Entities: miss ~20%, add some false positives
            predicted_ents = []
            for ent in clause.entities:
                if random.random() < 0.80:  # 80% recall
                    predicted_ents.append(ent)
            # Add a spurious entity 15% of the time
            if random.random() < 0.15:
                predicted_ents.append(EntitySpan(
                    text="spurious_entity",
                    entity_type="other",
                    start=0, end=10,
                ))
            clause.predicted_entities = predicted_ents

    return dataset


def main():
    parser = argparse.ArgumentParser(description="ContractAI Evaluation Framework")
    parser.add_argument("--live", action="store_true", help="Run against actual AI engine (uses API)")
    parser.add_argument("--dataset", type=str, help="Path to labeled dataset JSON")
    parser.add_argument("--output-dir", type=str, default="./data/eval_reports", help="Output directory for reports")
    parser.add_argument("--charts", action="store_true", help="Generate visualization charts (requires matplotlib)")
    parser.add_argument("--save-sample", type=str, help="Save sample dataset to this path and exit")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    # Save sample dataset if requested
    if args.save_sample:
        dataset = create_sample_dataset()
        save_dataset(dataset, args.save_sample)
        print(f"Sample dataset saved to: {args.save_sample}")
        return

    # Load or create dataset
    if args.dataset:
        print(f"Loading dataset from: {args.dataset}")
        dataset = load_dataset(args.dataset)
    else:
        print("Using sample dataset (pass --dataset for custom data)")
        dataset = create_sample_dataset()

    print(f"Dataset: {dataset.name}")
    print(f"Contracts: {len(dataset.samples)} | Clauses: {dataset.total_clauses}")
    print(f"Types: {', '.join(dataset.contract_types)}")
    print()

    # Run evaluation
    runner = EvaluationRunner()

    if args.live:
        print("Running LIVE evaluation (calling AI engine)...")
        result = asyncio.run(runner.run_live(dataset))
    else:
        print("Running OFFLINE evaluation (simulated predictions)...")
        dataset = _simulate_predictions(dataset)
        result = runner.run_offline(dataset)

    # Generate reports
    reporter = ReportGenerator()

    # Print text report
    text_report = reporter.to_text(result)
    print(text_report)

    # Save reports
    paths = reporter.save_report(result, output_dir)
    print(f"\nReports saved:")
    print(f"  JSON: {paths['json']}")
    print(f"  Text: {paths['text']}")

    # Generate charts
    if args.charts:
        try:
            from app.ai_engine.evaluation.charts import ChartGenerator
            chart_gen = ChartGenerator(output_dir / "charts")
            chart_paths = chart_gen.generate_all(result)
            print(f"\nCharts generated ({len(chart_paths)}):")
            for p in chart_paths:
                print(f"  {p}")
        except ImportError as e:
            print(f"\nSkipping charts: {e}")
            print("Install with: pip install matplotlib")

    # Return exit code based on thresholds
    passed = (
        result.classification.accuracy >= 0.70
        and result.entity.f1 >= 0.50
        and result.risk.mae <= 3.0
    )

    if passed:
        print("\n[PASS] All metrics within acceptable thresholds.")
    else:
        print("\n[WARN] Some metrics below threshold — review report.")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main() or 0)
