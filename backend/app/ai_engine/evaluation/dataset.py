"""Test dataset format and loader for the evaluation framework.

Dataset Format (JSON):
{
  "metadata": {
    "name": "ContractAI Evaluation Set v1",
    "created": "2026-08-01",
    "source": "manual annotation",
    "annotators": 2,
    "contract_types": ["employment", "nda", "service_agreement"]
  },
  "samples": [
    {
      "id": "eval_001",
      "contract_type": "employment",
      "text": "Full contract text...",
      "clauses": [
        {
          "id": "c1",
          "text": "The Employee shall not...",
          "true_category": "non_compete",
          "true_risk_score": 8,
          "entities": [
            {"text": "Employee", "type": "party", "start": 4, "end": 12},
            {"text": "2 years", "type": "duration", "start": 45, "end": 52}
          ]
        }
      ],
      "true_overall_risk": 72,
      "true_risk_dimensions": {
        "financial": 6.5,
        "liability": 8.0,
        "termination": 7.0,
        "compliance": 5.0,
        "privacy": 3.0
      }
    }
  ]
}
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

from app.ai_engine.evaluation.metrics import EntitySpan


@dataclass
class ClauseSample:
    """A single clause in the evaluation dataset."""
    id: str
    text: str
    true_category: str
    true_risk_score: float
    entities: list[EntitySpan] = field(default_factory=list)
    predicted_category: str | None = None
    predicted_risk_score: float | None = None
    predicted_entities: list[EntitySpan] | None = None


@dataclass
class ContractSample:
    """A full contract evaluation sample."""
    id: str
    contract_type: str
    text: str
    clauses: list[ClauseSample]
    true_overall_risk: float
    true_risk_dimensions: dict[str, float] = field(default_factory=dict)
    predicted_overall_risk: float | None = None
    predicted_risk_dimensions: dict[str, float] | None = None


@dataclass
class EvaluationDataset:
    """Complete evaluation dataset."""
    name: str
    samples: list[ContractSample]
    metadata: dict = field(default_factory=dict)

    @property
    def total_clauses(self) -> int:
        return sum(len(s.clauses) for s in self.samples)

    @property
    def contract_types(self) -> list[str]:
        return sorted(set(s.contract_type for s in self.samples))

    def filter_by_type(self, contract_type: str) -> "EvaluationDataset":
        filtered = [s for s in self.samples if s.contract_type == contract_type]
        return EvaluationDataset(name=f"{self.name} ({contract_type})", samples=filtered, metadata=self.metadata)


def load_dataset(path: str | Path) -> EvaluationDataset:
    """Load evaluation dataset from JSON file."""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    samples = []
    for s in data["samples"]:
        clauses = []
        for c in s["clauses"]:
            entities = [
                EntitySpan(text=e["text"], entity_type=e["type"], start=e.get("start", 0), end=e.get("end", 0))
                for e in c.get("entities", [])
            ]
            clauses.append(ClauseSample(
                id=c["id"],
                text=c["text"],
                true_category=c["true_category"],
                true_risk_score=c["true_risk_score"],
                entities=entities,
            ))
        samples.append(ContractSample(
            id=s["id"],
            contract_type=s["contract_type"],
            text=s["text"],
            clauses=clauses,
            true_overall_risk=s["true_overall_risk"],
            true_risk_dimensions=s.get("true_risk_dimensions", {}),
        ))

    return EvaluationDataset(
        name=data.get("metadata", {}).get("name", path.stem),
        samples=samples,
        metadata=data.get("metadata", {}),
    )


def save_dataset(dataset: EvaluationDataset, path: str | Path) -> None:
    """Save evaluation dataset to JSON file."""
    path = Path(path)
    data = {
        "metadata": {
            "name": dataset.name,
            **dataset.metadata,
        },
        "samples": [
            {
                "id": s.id,
                "contract_type": s.contract_type,
                "text": s.text,
                "true_overall_risk": s.true_overall_risk,
                "true_risk_dimensions": s.true_risk_dimensions,
                "clauses": [
                    {
                        "id": c.id,
                        "text": c.text,
                        "true_category": c.true_category,
                        "true_risk_score": c.true_risk_score,
                        "entities": [
                            {"text": e.text, "type": e.entity_type, "start": e.start, "end": e.end}
                            for e in c.entities
                        ],
                    }
                    for c in s.clauses
                ],
            }
            for s in dataset.samples
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def create_sample_dataset() -> EvaluationDataset:
    """Create a small sample dataset for testing the evaluation pipeline."""
    samples = [
        ContractSample(
            id="eval_001",
            contract_type="employment",
            text="EMPLOYMENT AGREEMENT between Acme Corp and John Doe...",
            true_overall_risk=68,
            true_risk_dimensions={"financial": 5.0, "liability": 8.0, "termination": 7.5, "compliance": 4.0, "privacy": 3.0},
            clauses=[
                ClauseSample(
                    id="c1",
                    text="Employee shall not engage in any competing business within a 50-mile radius for a period of 2 years following termination.",
                    true_category="non_compete",
                    true_risk_score=8,
                    entities=[
                        EntitySpan(text="Employee", entity_type="party", start=0, end=8),
                        EntitySpan(text="50-mile radius", entity_type="scope", start=62, end=76),
                        EntitySpan(text="2 years", entity_type="duration", start=95, end=102),
                    ],
                ),
                ClauseSample(
                    id="c2",
                    text="The Company shall pay Employee a base salary of $85,000 per annum, payable in bi-weekly installments.",
                    true_category="payment",
                    true_risk_score=2,
                    entities=[
                        EntitySpan(text="Company", entity_type="party", start=4, end=11),
                        EntitySpan(text="Employee", entity_type="party", start=22, end=30),
                        EntitySpan(text="$85,000", entity_type="amount", start=50, end=57),
                        EntitySpan(text="per annum", entity_type="frequency", start=58, end=67),
                    ],
                ),
                ClauseSample(
                    id="c3",
                    text="Employee agrees to indemnify and hold harmless the Company from any and all claims arising from Employee's negligence or willful misconduct.",
                    true_category="liability",
                    true_risk_score=7,
                    entities=[
                        EntitySpan(text="Employee", entity_type="party", start=0, end=8),
                        EntitySpan(text="Company", entity_type="party", start=49, end=56),
                    ],
                ),
                ClauseSample(
                    id="c4",
                    text="Either party may terminate this agreement with 30 days written notice.",
                    true_category="termination",
                    true_risk_score=3,
                    entities=[
                        EntitySpan(text="30 days", entity_type="duration", start=49, end=56),
                    ],
                ),
                ClauseSample(
                    id="c5",
                    text="All intellectual property created during employment shall be the sole and exclusive property of the Company.",
                    true_category="ip_rights",
                    true_risk_score=7,
                    entities=[
                        EntitySpan(text="Company", entity_type="party", start=99, end=106),
                    ],
                ),
            ],
        ),
        ContractSample(
            id="eval_002",
            contract_type="nda",
            text="MUTUAL NON-DISCLOSURE AGREEMENT between TechCo Inc and StartupXYZ...",
            true_overall_risk=35,
            true_risk_dimensions={"financial": 2.0, "liability": 4.0, "termination": 3.0, "compliance": 3.5, "privacy": 6.0},
            clauses=[
                ClauseSample(
                    id="c6",
                    text="Confidential Information shall mean all non-public information disclosed by either party.",
                    true_category="confidentiality",
                    true_risk_score=3,
                    entities=[
                        EntitySpan(text="either party", entity_type="party", start=75, end=87),
                    ],
                ),
                ClauseSample(
                    id="c7",
                    text="The obligations of confidentiality shall survive for 3 years from the date of disclosure.",
                    true_category="confidentiality",
                    true_risk_score=4,
                    entities=[
                        EntitySpan(text="3 years", entity_type="duration", start=53, end=60),
                    ],
                ),
                ClauseSample(
                    id="c8",
                    text="This Agreement shall be governed by the laws of the State of Delaware.",
                    true_category="governing_law",
                    true_risk_score=2,
                    entities=[
                        EntitySpan(text="State of Delaware", entity_type="jurisdiction", start=52, end=69),
                    ],
                ),
            ],
        ),
        ContractSample(
            id="eval_003",
            contract_type="service_agreement",
            text="SERVICE AGREEMENT between Client Corp and Provider LLC...",
            true_overall_risk=55,
            true_risk_dimensions={"financial": 6.5, "liability": 6.0, "termination": 5.0, "compliance": 4.0, "privacy": 4.5},
            clauses=[
                ClauseSample(
                    id="c9",
                    text="Provider shall deliver all work product within 30 days of the project start date. Late delivery shall incur a penalty of 2% of the project value per week.",
                    true_category="penalties",
                    true_risk_score=7,
                    entities=[
                        EntitySpan(text="Provider", entity_type="party", start=0, end=8),
                        EntitySpan(text="30 days", entity_type="duration", start=46, end=53),
                        EntitySpan(text="2%", entity_type="percentage", start=119, end=121),
                    ],
                ),
                ClauseSample(
                    id="c10",
                    text="Provider's total liability under this agreement shall not exceed the total fees paid in the preceding 12 months.",
                    true_category="liability",
                    true_risk_score=4,
                    entities=[
                        EntitySpan(text="Provider", entity_type="party", start=0, end=8),
                        EntitySpan(text="12 months", entity_type="duration", start=96, end=105),
                    ],
                ),
                ClauseSample(
                    id="c11",
                    text="Client may terminate this agreement immediately if Provider fails to cure a material breach within 15 days of written notice.",
                    true_category="termination",
                    true_risk_score=5,
                    entities=[
                        EntitySpan(text="Client", entity_type="party", start=0, end=6),
                        EntitySpan(text="Provider", entity_type="party", start=54, end=62),
                        EntitySpan(text="15 days", entity_type="duration", start=98, end=105),
                    ],
                ),
            ],
        ),
    ]

    return EvaluationDataset(
        name="ContractAI Sample Evaluation Set",
        samples=samples,
        metadata={
            "created": "2026-08-01",
            "source": "synthetic",
            "annotators": 1,
            "purpose": "pipeline testing",
        },
    )
