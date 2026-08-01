# AI Pipeline Architecture
## ContractAI Guardian — NLP Engineering Specification

---

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONTRACT AI PIPELINE                                 │
│                                                                             │
│  ┌──────────┐   ┌──────────┐   ┌───────┐   ┌──────────┐   ┌───────────┐  │
│  │  STAGE 1 │──▶│  STAGE 2 │──▶│STAGE 3│──▶│  STAGE 4 │──▶│  STAGE 5  │  │
│  │ Extract  │   │ Segment  │   │  NER  │   │ Classify │   │   Risk    │  │
│  └──────────┘   └──────────┘   └───────┘   └──────────┘   └───────────┘  │
│                                                                     │       │
│                                                                     ▼       │
│                                              ┌───────────┐   ┌───────────┐  │
│                                              │  STAGE 7  │◀──│  STAGE 6  │  │
│                                              │ Summarize │   │  Explain  │  │
│                                              └───────────┘   └───────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: Text Extraction

**Goal:** Raw bytes → clean, structured text.

```
INPUT (file bytes)
    │
    ├─── PDF (text-based) ──▶ pdf-parse ──▶ text + page structure
    │
    ├─── PDF (scanned) ─────▶ detect (no extractable text?)
    │                              │
    │                              ▼
    │                        pdf-to-image (pdf2pic)
    │                              │
    │                              ▼
    │                        OCR engine ──▶ text
    │
    ├─── DOCX ──────────────▶ mammoth ──▶ text + structure
    │
    └─── Image (JPG/PNG) ───▶ OCR engine ──▶ text
                                   │
                                   ▼
                          Post-processing
                                   │
                                   ▼
                          CLEAN STRUCTURED TEXT
```

### OCR Sub-pipeline

```
Raw Image
    │
    ▼
┌─────────────────────────────┐
│  Preprocessing              │
│  • Deskew (detect rotation) │
│  • Binarize (Otsu's)       │
│  • Denoise (median filter)  │
│  • Contrast normalization   │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  OCR Engine Selection       │
│                             │
│  IF clean scan:             │
│    → Tesseract 5 (free)    │
│                             │
│  IF low confidence (<80%):  │
│    → Google Cloud Vision    │
│      (fallback, paid)       │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Post-processing            │
│  • Spell correction         │
│  • Layout reconstruction    │
│  • Table detection          │
│  • Header/footer removal    │
│  • Page number stripping    │
└─────────────┬───────────────┘
              │
              ▼
        Clean text output
```

### Technology

| Component | Choice | Why |
|-----------|--------|-----|
| PDF text extraction | pdf-parse (Node) / PyMuPDF (Python) | Fast, preserves layout |
| PDF-to-image | pdf2pic / pdf-poppler | Needed for scanned PDFs |
| OCR primary | Tesseract 5 with `eng+legal` training data | Free, good for clean scans |
| OCR fallback | Google Cloud Vision API | Superior on degraded inputs |
| DOCX parsing | mammoth | Preserves semantic structure |
| Image preprocessing | sharp (Node) / Pillow (Python) | Deskew, binarize |

### Output Format

```json
{
  "raw_text": "Full extracted text...",
  "pages": [
    { "page": 1, "text": "...", "confidence": 0.97 }
  ],
  "structure": {
    "headings": [
      { "level": 1, "text": "EMPLOYMENT AGREEMENT", "page": 1, "offset": 0 }
    ],
    "tables": [
      { "page": 3, "rows": [["Term", "Value"], ["Salary", "$120,000"]] }
    ]
  },
  "metadata": {
    "source_type": "pdf_text",
    "pages_count": 12,
    "word_count": 8450,
    "language": "en",
    "ocr_used": false,
    "avg_confidence": 0.98
  }
}
```

---

## Stage 2: Clause Segmentation

**Goal:** Continuous text → array of discrete clauses with boundaries.

```
CLEAN TEXT
    │
    ▼
┌────────────────────────────────────────────┐
│  Rule-Based Pre-segmentation               │
│                                            │
│  Split on:                                 │
│  • Numbered sections (1., 1.1, (a), (i))  │
│  • ALL-CAPS headings                       │
│  • Bold/underlined headings (from DOCX)    │
│  • "ARTICLE", "SECTION", "CLAUSE" markers  │
│  • Double newlines (fallback)              │
└──────────────────┬─────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────┐
│  LLM Refinement Pass                       │
│                                            │
│  Prompt: "Given these pre-segmented chunks,│
│  identify any that should be merged (same  │
│  logical clause split by formatting) or    │
│  split (multiple topics in one section)."  │
│                                            │
│  Model: Claude Haiku (fast, cheap)         │
└──────────────────┬─────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────┐
│  Hierarchy Assignment                      │
│                                            │
│  • Article > Section > Subsection          │
│  • Parent-child relationships              │
│  • Cross-reference detection               │
│    ("as defined in Section 2.3")           │
└──────────────────┬─────────────────────────┘
                   │
                   ▼
            CLAUSE ARRAY
```

### Segmentation Strategy

**Why hybrid (rules + LLM)?**
- Rules alone fail on poorly formatted contracts (no section numbers, inconsistent headings)
- LLM alone is expensive for a structural task that's mostly regex-solvable
- Rules handle 80% → LLM fixes the remaining 20%

### Segmentation Rules (Priority Order)

```
1. ARTICLE/SECTION markers:
   /^(ARTICLE|SECTION|CLAUSE)\s+[IVXLCDM\d]+/i

2. Numbered sections:
   /^\d+(\.\d+)*[\.\)]\s+[A-Z]/

3. Lettered subsections:
   /^\([a-z]\)\s+/

4. ALL-CAPS headings (min 3 words):
   /^[A-Z][A-Z\s]{10,}$/

5. Paragraph breaks (fallback):
   /\n{2,}/
```

### Output Format

```json
{
  "clauses": [
    {
      "id": "clause_001",
      "section_number": "1",
      "title": "Definitions",
      "text": "For the purposes of this Agreement...",
      "parent_id": null,
      "children": ["clause_001a", "clause_001b"],
      "start_offset": 0,
      "end_offset": 847,
      "page": 1,
      "cross_references": ["clause_005", "clause_012"]
    }
  ],
  "hierarchy": {
    "clause_001": ["clause_001a", "clause_001b"],
    "clause_005": ["clause_005_1", "clause_005_2"]
  }
}
```

---

## Stage 3: Named Entity Recognition (NER)

**Goal:** Extract structured entities from each clause and from the contract as a whole.

```
CLAUSE ARRAY
    │
    ├──────────────────────────────────────────────────────┐
    │                                                      │
    ▼                                                      ▼
┌──────────────────────────┐          ┌──────────────────────────────┐
│  Standard NER            │          │  Legal Domain NER             │
│  (spaCy / Claude)        │          │  (Claude with legal prompts)  │
│                          │          │                               │
│  • PERSON               │          │  • PAYMENT_TERM               │
│  • ORG                  │          │  • PENALTY                    │
│  • DATE                 │          │  • LIABILITY_TERM             │
│  • MONEY               │          │  • OBLIGATION                 │
│  • PERCENT             │          │  • TERMINATION_CONDITION      │
│  • DURATION            │          │  • DEADLINE                   │
│  • LOCATION            │          │  • RESTRICTION                │
└───────────┬──────────────┘          └──────────────┬───────────────┘
            │                                        │
            └────────────────┬───────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Entity Linking  │
                    │  & Resolution    │
                    │                  │
                    │  "Company" =     │
                    │  "Acme Corp" =   │
                    │  "Employer"      │
                    └────────┬────────┘
                             │
                             ▼
                    ENTITY REGISTRY
```

### Entity Types

#### Standard Entities (extractable with spaCy + rules)

| Entity | Pattern | Example |
|--------|---------|---------|
| PERSON | NER model + "hereinafter" patterns | "Jane Doe (hereinafter 'Employee')" |
| ORG | NER model + "Inc/LLC/Ltd" patterns | "Acme Corporation" |
| DATE | dateutil parsing + relative date resolution | "January 1, 2026", "30 days after execution" |
| MONEY | Currency + number patterns | "$150,000", "USD 5,000 per month" |
| PERCENT | Number + % | "1.5% per month", "fifteen percent (15%)" |
| DURATION | Temporal expressions | "twenty-four (24) months", "2 years" |
| LOCATION | NER model + jurisdiction patterns | "State of California", "New York County" |

#### Legal Domain Entities (require LLM extraction)

| Entity | What to Extract | Example |
|--------|----------------|---------|
| PAYMENT_TERM | {amount, frequency, due_date, condition, method} | "$5,000 monthly, due 15th, net-30" |
| PENALTY | {trigger, consequence, amount, cap} | "Late fee of 1.5%/month on overdue balance" |
| LIABILITY_TERM | {party, scope, cap, exclusions, indemnification} | "Contractor liable for direct damages, capped at fees paid" |
| OBLIGATION | {party, action, deadline, standard} | "Deliver reports quarterly, commercially reasonable efforts" |
| TERMINATION_CONDITION | {trigger, notice, cure_period, consequences} | "30 days written notice, 15-day cure period" |
| DEADLINE | {date, action, consequence_of_miss} | "File by March 15 or forfeit deposit" |
| RESTRICTION | {party, restriction, scope, duration, geography} | "Non-compete, 50-mile radius, 2 years" |

### NER Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    TWO-PASS NER APPROACH                         │
│                                                                 │
│  PASS 1: Rule-based + spaCy (fast, free)                       │
│  ──────────────────────────────────────                         │
│  • Extract: PERSON, ORG, DATE, MONEY, PERCENT, DURATION        │
│  • Method: spaCy en_core_web_trf + regex patterns              │
│  • Cost: ~0 (local inference)                                   │
│  • Time: <2s for full contract                                  │
│                                                                 │
│  PASS 2: LLM extraction (accurate, contextual)                 │
│  ─────────────────────────────────────────────                  │
│  • Extract: PAYMENT_TERM, PENALTY, LIABILITY, OBLIGATION, etc. │
│  • Method: Claude with structured output schema                 │
│  • Cost: ~$0.02-0.05 per contract                              │
│  • Time: ~10-15s                                                │
│                                                                 │
│  WHY TWO PASSES:                                                │
│  • Pass 1 catches the easy stuff cheaply                       │
│  • Pass 2 gets the hard legal semantics with context            │
│  • Pass 1 results feed into Pass 2 prompt (grounding)          │
└─────────────────────────────────────────────────────────────────┘
```

### Entity Resolution

```
Reference Resolution:
  "the Company" → "Acme Corporation"
  "Employer" → "Acme Corporation"
  "Party A" → "Acme Corporation"

Date Resolution:
  "30 days after execution" → "2026-02-14" (if execution date = 2026-01-15)
  "within the Term" → "2026-01-15 to 2027-01-14"

Amount Resolution:
  "fifteen thousand dollars ($15,000)" → { amount: 15000, currency: "USD" }
  "the Fee" → { amount: 5000, currency: "USD", ref: "clause_004" }
```

### Output Format

```json
{
  "entities": {
    "parties": [
      {
        "name": "Acme Corporation",
        "type": "organization",
        "role": "employer",
        "aliases": ["the Company", "Employer", "Party A"],
        "first_mention": { "clause_id": "clause_001", "offset": 45 }
      }
    ],
    "dates": [
      {
        "value": "2026-01-15",
        "type": "effective_date",
        "original_text": "January 15, 2026",
        "clause_id": "clause_002"
      }
    ],
    "money": [
      {
        "amount": 120000,
        "currency": "USD",
        "frequency": "annual",
        "context": "base_salary",
        "original_text": "one hundred twenty thousand dollars ($120,000) per annum",
        "clause_id": "clause_004"
      }
    ],
    "payment_terms": [
      {
        "amount": 10000,
        "currency": "USD",
        "frequency": "monthly",
        "due": "last business day",
        "method": "direct deposit",
        "clause_id": "clause_004"
      }
    ],
    "penalties": [
      {
        "trigger": "termination before 12 months",
        "consequence": "repay signing bonus",
        "amount": 25000,
        "cap": null,
        "clause_id": "clause_009"
      }
    ],
    "liabilities": [
      {
        "party": "Acme Corporation",
        "scope": "all direct and indirect damages",
        "cap": null,
        "exclusions": [],
        "clause_id": "clause_012"
      }
    ]
  }
}
```

---

## Stage 4: Clause Classification

**Goal:** Assign one or more category labels to each clause with confidence scores.

```
CLAUSE (text + entities)
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│              CLASSIFICATION APPROACH                          │
│                                                             │
│  PRIMARY: Claude (zero-shot classification)                 │
│  ─────────────────────────────────────────                  │
│  Prompt with category definitions + few-shot examples        │
│  Returns: top categories with confidence scores              │
│                                                             │
│  FALLBACK (cost optimization, phase 2):                     │
│  ─────────────────────────────────────────                  │
│  Fine-tuned classifier for high-volume screening             │
│  (SetFit or sentence-transformers + logistic regression)     │
│  LLM only for ambiguous cases (confidence < 0.7)            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Category Taxonomy

```
CONTRACT CLAUSE CATEGORIES
│
├── PAYMENT
│   ├── Compensation / Pricing
│   ├── Payment Schedule
│   ├── Late Payment / Interest
│   ├── Expenses / Reimbursement
│   └── Taxes
│
├── TERMINATION
│   ├── For Cause
│   ├── For Convenience
│   ├── Automatic Expiration
│   ├── Mutual Termination
│   └── Effects of Termination
│
├── LIABILITY
│   ├── Limitation of Liability
│   ├── Indemnification
│   ├── Hold Harmless
│   ├── Disclaimer
│   └── Insurance Requirements
│
├── CONFIDENTIALITY
│   ├── Definition of Confidential Info
│   ├── Obligations
│   ├── Exceptions
│   ├── Duration
│   └── Return/Destruction
│
├── INTELLECTUAL_PROPERTY
│   ├── Ownership / Assignment
│   ├── Work for Hire
│   ├── License Grant
│   ├── Pre-existing IP
│   └── Moral Rights
│
├── DATA_PRIVACY
│   ├── Data Processing
│   ├── Data Protection
│   ├── Breach Notification
│   ├── Data Subject Rights
│   └── Cross-border Transfer
│
├── WARRANTY
│   ├── Representations
│   ├── Express Warranty
│   ├── Warranty Disclaimer
│   └── Remedy
│
├── DISPUTE_RESOLUTION
│   ├── Governing Law
│   ├── Jurisdiction
│   ├── Arbitration
│   ├── Mediation
│   └── Attorney's Fees
│
├── NON_COMPETE
│   ├── Non-competition
│   ├── Non-solicitation
│   ├── Geographic Scope
│   └── Duration
│
├── PENALTIES
│   ├── Liquidated Damages
│   ├── Service Level Credits
│   └── Clawback
│
└── OTHER
    ├── Force Majeure
    ├── Assignment
    ├── Notices
    ├── Entire Agreement
    ├── Amendments
    ├── Severability
    └── Definitions
```

### Classification Prompt Strategy

```
SYSTEM PROMPT (for Claude):
───────────────────────────
You are a legal document classifier. Given a contract clause,
assign one or more categories from the taxonomy below.

Rules:
- Assign the MOST SPECIFIC subcategory that applies
- A clause can have multiple categories (max 3)
- Assign confidence 0.0-1.0 for each
- If a clause is purely boilerplate definitions, classify as OTHER/Definitions

Categories:
[full taxonomy inserted here]

Output JSON:
{
  "categories": [
    {"category": "LIABILITY/Indemnification", "confidence": 0.92},
    {"category": "PAYMENT/Expenses", "confidence": 0.35}
  ],
  "primary_category": "LIABILITY"
}

FEW-SHOT EXAMPLES:
[5-10 examples per category from training set]
```

### Multi-Label Classification Logic

```
┌──────────────────────────────────────────────┐
│  Classification Decision Flow                 │
│                                              │
│  1. Claude assigns categories + confidence    │
│                                              │
│  2. Filter: keep categories with conf > 0.3  │
│                                              │
│  3. Primary = highest confidence category     │
│                                              │
│  4. If highest confidence < 0.5:             │
│     → flag for review                        │
│     → classify as OTHER with note            │
│                                              │
│  5. If 2+ categories with conf > 0.7:       │
│     → multi-category clause                  │
│     → analyze for EACH category separately   │
└──────────────────────────────────────────────┘
```

### Output Format

```json
{
  "clause_id": "clause_012",
  "classifications": [
    {
      "category": "LIABILITY",
      "subcategory": "Limitation of Liability",
      "confidence": 0.94,
      "evidence": "contains 'shall not be liable', 'in no event', damage cap language"
    },
    {
      "category": "PENALTIES",
      "subcategory": "Liquidated Damages",
      "confidence": 0.41,
      "evidence": "references specific dollar amount as consequence"
    }
  ],
  "primary_category": "LIABILITY",
  "is_standard": true,
  "complexity": "moderate"
}
```

---

## Stage 5: Risk Prediction

**Goal:** Score each clause and the overall contract for risk, with explanations.

```
CLAUSE + CLASSIFICATION + ENTITIES
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RISK ASSESSMENT ENGINE                         │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  RISK SIGNALS (what the model looks for)                  │  │
│  │                                                           │  │
│  │  Financial:                                               │  │
│  │  • No liability cap → +3 risk                            │  │
│  │  • Unlimited indemnification → +4 risk                   │  │
│  │  • Penalty without cap → +2 risk                         │  │
│  │  • Asymmetric payment terms → +1 risk                    │  │
│  │                                                           │  │
│  │  Restrictive:                                             │  │
│  │  • Non-compete > 1 year → +2 risk                        │  │
│  │  • Broad IP assignment (includes pre-existing) → +3 risk │  │
│  │  • Exclusive dealing → +2 risk                           │  │
│  │                                                           │  │
│  │  One-sided:                                               │  │
│  │  • Only one party can terminate → +2 risk                │  │
│  │  • Unilateral amendment rights → +3 risk                 │  │
│  │  • Asymmetric liability → +2 risk                        │  │
│  │                                                           │  │
│  │  Missing:                                                 │  │
│  │  • No termination clause → +2 risk                       │  │
│  │  • No dispute resolution → +1 risk                       │  │
│  │  • No liability cap → +3 risk                            │  │
│  │  • No force majeure → +1 risk                            │  │
│  │                                                           │  │
│  │  Unusual:                                                 │  │
│  │  • Non-standard language obscuring meaning → +2 risk     │  │
│  │  • Vague scope ("all services") → +1 risk               │  │
│  │  • Conflicting clauses → +2 risk                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  SCORING APPROACH                                         │  │
│  │                                                           │  │
│  │  Clause Score = LLM assessment (1-10) guided by signals   │  │
│  │                                                           │  │
│  │  Contract Score = weighted_average(clause_scores)         │  │
│  │    where weight = category_importance × clause_severity   │  │
│  │                                                           │  │
│  │  Category weights:                                        │  │
│  │    LIABILITY: 2.0                                         │  │
│  │    TERMINATION: 1.8                                       │  │
│  │    PENALTIES: 1.8                                         │  │
│  │    NON_COMPETE: 1.5                                       │  │
│  │    IP_RIGHTS: 1.5                                         │  │
│  │    PAYMENT: 1.3                                           │  │
│  │    CONFIDENTIALITY: 1.0                                   │  │
│  │    WARRANTY: 1.0                                          │  │
│  │    DISPUTE: 0.8                                           │  │
│  │    OTHER: 0.5                                             │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Risk Prompt Strategy

```
SYSTEM PROMPT:
──────────────
You are a contract risk analyst. For each clause, assess risk
to the READER (the person uploading this contract, not the drafter).

Score 1-10 where:
  1-2: Standard, fair, balanced
  3-4: Slightly unfavorable but common
  5-6: Meaningfully one-sided, user should understand
  7-8: Significantly risky, should negotiate
  9-10: Dangerous, do not sign without changes

For each clause provide:
1. Risk score (1-10)
2. Risk category (from list)
3. One-sentence explanation of the risk
4. Concrete consequence ("If X happens, then Y")
5. Whether this is standard for this contract type

Consider:
- The contract type: {contract_type}
- Who the user is: {user_role} (e.g., "employee", "tenant", "contractor")
- What's normal for this type of agreement
- Compounding effects with other clauses

CRITICAL: Explain risks in terms of REAL CONSEQUENCES, not legal abstractions.
  BAD:  "This clause limits your remedies"
  GOOD: "If their software deletes your data, the most you can recover is $500"
```

### Compounding Risk Detection

```
┌──────────────────────────────────────────────────────────┐
│  COMPOUNDING RISK ANALYSIS                                │
│                                                          │
│  After individual clause scoring:                         │
│                                                          │
│  1. Identify related clause pairs:                       │
│     • Liability + Indemnification                        │
│     • Non-compete + IP Assignment                        │
│     • Termination + Penalty                              │
│     • Payment + Late Fee + Termination for non-payment   │
│                                                          │
│  2. Assess combined effect:                              │
│     "Clause A says unlimited liability AND Clause B      │
│      says you indemnify them for third-party claims.     │
│      Together: you're on the hook for anything that      │
│      goes wrong, even things you didn't cause."          │
│                                                          │
│  3. Adjust contract score upward if compounds exist      │
│     (+1 per compounding pair, max +3)                    │
└──────────────────────────────────────────────────────────┘
```

### Output Format

```json
{
  "contract_risk": {
    "score": 7,
    "label": "High",
    "summary": "Significantly one-sided liability terms with no cap, combined with broad IP assignment.",
    "user_perspective": "employee"
  },
  "clause_risks": [
    {
      "clause_id": "clause_012",
      "score": 9,
      "label": "Critical",
      "category": "financial_exposure",
      "explanation": "You accept unlimited personal liability for any damages.",
      "consequence": "If a project fails and they lose a client worth $1M, they could sue YOU for that full amount — your savings, house, everything is exposed.",
      "is_standard": false,
      "standard_would_be": "Liability capped at total fees paid (typically $50K-100K for this type of contract)"
    }
  ],
  "compounding_risks": [
    {
      "clauses": ["clause_012", "clause_013"],
      "combined_score": 10,
      "explanation": "Unlimited liability (Clause 12) + broad indemnification (Clause 13) = you cover all their losses AND their legal fees defending against third parties. Double exposure."
    }
  ],
  "missing_protections": [
    {
      "missing": "Liability cap",
      "importance": "critical",
      "standard_language": "total liability shall not exceed fees paid in prior 12 months"
    }
  ]
}
```

---

## Stage 6: Explainability Layer

**Goal:** Transform every analysis output into non-lawyer language following the 4-question framework.

```
RISK ANALYSIS OUTPUT
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  EXPLANATION GENERATOR                               │
│                                                     │
│  Input:                                             │
│  • Clause original text                             │
│  • Classification result                            │
│  • Risk score + category                            │
│  • Extracted entities (numbers, dates)              │
│  • Contract type + user role                        │
│                                                     │
│  Output (per clause):                               │
│  ┌─────────────────────────────────────────────┐    │
│  │  TL;DR: [one sentence]                      │    │
│  │                                             │    │
│  │  WHAT DOES THIS MEAN?                       │    │
│  │  [2-3 sentences, grade 8 reading level]     │    │
│  │                                             │    │
│  │  WHY SHOULD I CARE?                         │    │
│  │  [1-2 sentences, personal stakes]           │    │
│  │                                             │    │
│  │  WHAT CAN HAPPEN?                           │    │
│  │  [worst-case scenario, concrete]            │    │
│  │                                             │    │
│  │  WHAT SHOULD I NEGOTIATE?                   │    │
│  │  [actionable suggestion with language]      │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Explanation Prompt Strategy

```
SYSTEM PROMPT:
──────────────
You are explaining a contract clause to someone with NO legal knowledge.

Context:
- Contract type: {contract_type}
- User role: {user_role}
- Clause category: {category}
- Risk level: {risk_score}/10

Rules:
1. NEVER use legal jargon without immediate explanation
2. Use "you" and "they" — make it personal
3. Include SPECIFIC numbers/dates from the clause
4. Worst case must be CONCRETE ("you lose $X" not "financial impact")
5. Negotiation suggestions must include exact alternative wording
6. Reading level: 8th grade maximum
7. If something is standard/normal, say so — don't alarm unnecessarily

Banned phrases:
- "may have implications"
- "could potentially"
- "it is advisable to"
- "pursuant to"
- "notwithstanding"
- "herein"

Replace with:
- "this means [specific thing]"
- "this will [specific consequence]"
- "you should ask for [specific change]"
```

### Adaptive Tone Matrix

```
┌────────────────────┬─────────────────────────────────────┐
│  Contract Type     │  Tone Adaptation                    │
├────────────────────┼─────────────────────────────────────┤
│  Employment        │  "your employer" / "your boss"      │
│                    │  Frame as workplace rights           │
├────────────────────┼─────────────────────────────────────┤
│  Lease             │  "your landlord" / "the property"   │
│                    │  Frame as home security              │
├────────────────────┼─────────────────────────────────────┤
│  Freelance/Svc     │  "your client" / "the company"     │
│                    │  Frame as business protection        │
├────────────────────┼─────────────────────────────────────┤
│  NDA               │  "the other company"                │
│                    │  Frame as information freedom        │
├────────────────────┼─────────────────────────────────────┤
│  SaaS/Terms        │  "the service" / "the platform"    │
│                    │  Frame as user rights                │
├────────────────────┼─────────────────────────────────────┤
│  Loan              │  "the lender" / "the bank"          │
│                    │  Frame as financial exposure          │
└────────────────────┴─────────────────────────────────────┘
```

---

## Stage 7: Contract Summarization

**Goal:** Generate a structured summary of the entire contract that captures the key facts in <30 seconds of reading.

```
ALL PREVIOUS STAGE OUTPUTS
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│  SUMMARIZATION ENGINE                                        │
│                                                             │
│  Layer 1: Executive Summary (3-5 sentences)                 │
│  ──────────────────────────────────────────                 │
│  What is this contract? Who are the parties?                 │
│  What are you agreeing to? Key dates. Main risk.             │
│                                                             │
│  Layer 2: Key Facts Table                                   │
│  ────────────────────────                                   │
│  | Type | Parties | Duration | Value | Risk Score |         │
│                                                             │
│  Layer 3: Obligation Summary (per party)                    │
│  ──────────────────────────────────────                     │
│  YOU must: [list]                                           │
│  THEY must: [list]                                          │
│                                                             │
│  Layer 4: Risk Highlights                                   │
│  ────────────────────────                                   │
│  Top 3 risks with one-line explanations                     │
│                                                             │
│  Layer 5: Action Items                                      │
│  ──────────────────────                                     │
│  What to negotiate, what to verify, what to accept          │
└─────────────────────────────────────────────────────────────┘
```

### Summary Output Format

```json
{
  "executive_summary": "This is a 2-year employment agreement between you and Acme Corp as a Senior Engineer. Base salary $120K + equity. Key concern: unlimited liability clause and 2-year non-compete that's broader than industry standard.",

  "key_facts": {
    "contract_type": "Employment Agreement",
    "parties": ["You (Employee)", "Acme Corporation (Employer)"],
    "effective_date": "2026-01-15",
    "duration": "2 years, auto-renewing",
    "total_value": "$240,000 base + equity",
    "risk_score": 7
  },

  "obligations": {
    "you_must": [
      "Perform duties as Senior Engineer",
      "Maintain confidentiality for 5 years after leaving",
      "Not compete within 50 miles for 2 years after leaving",
      "Assign all IP created during employment"
    ],
    "they_must": [
      "Pay $10,000/month by last business day",
      "Provide health insurance after 90 days",
      "Give 30 days notice before termination"
    ]
  },

  "top_risks": [
    { "rank": 1, "summary": "Unlimited personal liability — no cap on damages", "score": 9 },
    { "rank": 2, "summary": "2-year non-compete blocks you from entire industry", "score": 8 },
    { "rank": 3, "summary": "All IP assigned including side projects", "score": 7 }
  ],

  "action_items": {
    "negotiate": ["Liability cap", "Non-compete duration", "Side project carve-out"],
    "verify": ["Equity vesting schedule (not in this document)", "Health insurance details"],
    "acceptable": ["Salary terms", "Confidentiality scope", "Termination notice period"]
  }
}
```

---

## Complete Pipeline Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        FULL PIPELINE EXECUTION                                   │
│                                                                                 │
│  TIME ──────────────────────────────────────────────────────────────────▶       │
│                                                                                 │
│  0s        5s         15s        25s        35s        45s        55s           │
│  │         │          │          │          │          │          │             │
│  ▼         ▼          ▼          ▼          ▼          ▼          ▼             │
│  ┌────┐  ┌─────┐   ┌─────┐   ┌─────────────────────────────────────┐          │
│  │ S1 │  │ S2  │   │ S3  │   │     SINGLE LLM CALL (Claude)        │          │
│  │Ext │  │ Seg │   │ NER │   │                                     │          │
│  │ract│  │ment │   │Pass1│   │  Combines: S3-Pass2 + S4 + S5 + S6  │          │
│  └────┘  └─────┘   └─────┘   │  + S7 in ONE structured prompt      │          │
│                               │                                     │          │
│  LOCAL    LOCAL+    LOCAL     │  Input: text + clauses + basic NER  │          │
│           HAIKU               │  Output: full analysis JSON          │          │
│                               └─────────────────────────────────────┘          │
│                                                                                 │
│  COST BREAKDOWN:                                                                │
│  • S1: $0 (local)                                                               │
│  • S2: $0.005 (Haiku for refinement)                                           │
│  • S3 Pass 1: $0 (spaCy local)                                                 │
│  • S3-S7 combined: $0.05-0.15 (one Claude Sonnet call, ~20K input tokens)      │
│  • TOTAL: ~$0.06-0.16 per contract                                             │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Why One Big LLM Call (not 5 separate)?

```
SEPARATE CALLS:                      ONE COMBINED CALL:
─────────────────                    ──────────────────
S3 NER:        $0.03, 8s            All at once:  $0.10, 20s
S4 Classify:   $0.03, 8s
S5 Risk:       $0.05, 12s           SAVES:
S6 Explain:    $0.05, 12s           • 30s latency (parallel vs sequential)
S7 Summary:    $0.03, 8s            • $0.09 cost (less prompt overhead)
───────────────────────              • Context shared (no re-reading contract)
Total:         $0.19, 48s
```

**Architecture decision:** Stages 3-7 run as ONE Claude call with a large structured output schema. The model sees the full contract once and produces all analysis in a single pass. This is cheaper and faster than sequential calls, and the model can cross-reference between stages (e.g., risk scoring informed by NER results).

For contracts >100K tokens: split into 2 calls (chunk analysis + synthesis).

---

## Model Recommendations

### Production Stack

| Stage | Model | Why |
|-------|-------|-----|
| Clause segmentation (refinement) | Claude Haiku 4.5 | Fast, cheap, structural task |
| Main analysis (NER + Classify + Risk + Explain + Summary) | Claude Sonnet 5 | Best quality/cost ratio for reasoning tasks |
| Chat (follow-up questions) | Claude Sonnet 5 | Needs reasoning + grounding |
| Contract comparison | Claude Opus 4.8 | Complex multi-document reasoning |
| Fallback / high-stakes re-analysis | Claude Opus 4.8 | Maximum accuracy when needed |

### Why Claude Over Alternatives

| Consideration | Claude | GPT-4 | Open Source (Llama/Mistral) |
|---------------|--------|--------|-----------------------------|
| 200K context window | Yes | 128K (GPT-4o) | 32K-128K |
| Structured JSON output | Excellent | Good | Inconsistent |
| Legal text comprehension | Excellent | Good | Mediocre |
| Cost (per 1M input tokens) | $3 (Sonnet) | $2.50 (4o) | Free but hosting costs |
| Latency | ~15-25s | ~10-20s | Variable |
| Grounding (stays on document) | Excellent | Good | Poor |

**Decision:** Claude Sonnet 5 as primary. Single provider, single API to manage. The 200K context window means no chunking for 95% of contracts. Switch to Opus for comparison tasks or when user explicitly requests "deep analysis."

### Alternative: Local Models (Phase 3, cost optimization)

```
HIGH VOLUME OPTIMIZATION (>10K contracts/day):
──────────────────────────────────────────────

Replace Pass 1 (NER + Classification) with local models:
• NER: spaCy en_core_web_trf (free, fast)
• Classification: fine-tuned SetFit model (free after training)
• Risk keywords: rule-based pre-filter

Keep Claude ONLY for:
• Risk scoring (needs reasoning)
• Explanations (needs natural language generation)
• Chat (needs context understanding)

Estimated cost reduction: 40-60%
```

---

## Training & Fine-tuning Strategy

### Phase 1: Zero-shot + Prompt Engineering (NOW)

No training needed. Ship with:

```
┌────────────────────────────────────────────────────────┐
│  PROMPT ENGINEERING STACK                               │
│                                                        │
│  1. System prompt with role + rules + taxonomy         │
│  2. Few-shot examples (5-10 per category)              │
│  3. Structured output schema (JSON mode)               │
│  4. Chain-of-thought for risk reasoning                │
│  5. Self-consistency check prompt (optional, phase 2)  │
└────────────────────────────────────────────────────────┘
```

### Phase 2: Prompt Optimization (Month 2-3)

Collect production data → optimize prompts:

```
USER UPLOADS CONTRACT
        │
        ▼
  ANALYSIS GENERATED
        │
        ├──▶ User feedback: 👍/👎 on each clause analysis
        │
        ├──▶ Click-through data: which explanations users read
        │
        └──▶ Chat questions: what the analysis MISSED
                │
                ▼
        PROMPT REFINEMENT
        • Add failure cases as few-shot negative examples
        • Tune risk thresholds based on user feedback
        • Add contract-type-specific prompt variants
```

### Phase 3: Fine-tuning (Month 4+, only if needed)

```
┌─────────────────────────────────────────────────────────────────┐
│  FINE-TUNING DECISION TREE                                       │
│                                                                 │
│  Q: Is Claude's zero-shot accuracy >90% on your eval set?       │
│  │                                                              │
│  ├── YES → Don't fine-tune. Improve prompts.                    │
│  │                                                              │
│  └── NO → What's failing?                                       │
│       │                                                         │
│       ├── Classification accuracy → Fine-tune SetFit classifier │
│       │   • Dataset: 200+ labeled clauses per category          │
│       │   • Model: sentence-transformers/all-MiniLM-L6-v2       │
│       │   • Method: SetFit (few-shot fine-tuning)               │
│       │   • Training: <1 hour on single GPU                     │
│       │                                                         │
│       ├── NER accuracy → Fine-tune spaCy NER                   │
│       │   • Dataset: 500+ annotated contracts                   │
│       │   • Annotations: Prodigy or Label Studio                │
│       │   • Training: spaCy train pipeline                      │
│       │                                                         │
│       └── Risk/Explanation quality → NOT fine-tunable           │
│           • These need reasoning, not pattern matching           │
│           • Fix with better prompts + more examples             │
│           • Or upgrade to Claude Opus                            │
└─────────────────────────────────────────────────────────────────┘
```

### Datasets for Training/Evaluation

| Dataset | Purpose | Source |
|---------|---------|--------|
| CUAD (Contract Understanding Atticus Dataset) | Clause classification eval | Public, 510 contracts, 41 categories |
| LEDGAR | Clause classification training | Public, 80K provisions from SEC filings |
| Contract-NLI | Entailment/contradiction in contracts | Public, Stanford |
| MAUD (Merger Agreement Understanding Dataset) | Complex clause analysis | Public, 152 merger agreements |
| Custom eval set | Production accuracy tracking | Build from first 100 user contracts (with consent) |

### Evaluation Framework

```
┌─────────────────────────────────────────────────────────────┐
│  EVAL METRICS (run weekly on test set)                        │
│                                                             │
│  Extraction (Stage 3):                                      │
│  • Entity F1 score (target: >0.90)                          │
│  • Date extraction accuracy (target: >0.95)                 │
│  • Money extraction accuracy (target: >0.95)                │
│                                                             │
│  Classification (Stage 4):                                  │
│  • Macro F1 across categories (target: >0.88)              │
│  • Per-category precision/recall                            │
│  • Confusion matrix for common misclassifications           │
│                                                             │
│  Risk (Stage 5):                                            │
│  • Score correlation with human labels (target: r>0.80)    │
│  • Critical risk recall (target: >0.95 — never miss a 9+)  │
│  • False alarm rate for low-risk clauses (target: <10%)     │
│                                                             │
│  Explanation (Stage 6):                                     │
│  • Flesch-Kincaid grade level (target: ≤8)                 │
│  • Factual accuracy vs source clause (target: 100%)        │
│  • User comprehension score (A/B test, target: >90%)       │
│                                                             │
│  End-to-end:                                                │
│  • User satisfaction (👍 rate, target: >80%)                │
│  • Chat grounding accuracy (0% hallucination)              │
│  • Processing time P95 (target: <60s)                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Prompt Engineering Strategy (Detailed)

### Master Analysis Prompt Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  PROMPT ARCHITECTURE (single-call analysis)                      │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  SYSTEM MESSAGE                                     │        │
│  │  • Role: Senior contract analyst                    │        │
│  │  • Output: Strict JSON schema                       │        │
│  │  • Rules: grounding, no hallucination, grade 8      │        │
│  │  • Category taxonomy (full)                         │        │
│  │  • Risk scoring criteria (detailed)                 │        │
│  │  • Explanation format (4-question framework)        │        │
│  │  • 5 few-shot examples (diverse contract types)     │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  USER MESSAGE                                       │        │
│  │  • Contract metadata (type hint, page count)        │        │
│  │  • User context (role, what they care about)        │        │
│  │  • Pre-segmented clauses (from Stage 2)             │        │
│  │  • Basic NER results (from Stage 3 Pass 1)         │        │
│  │  • Full contract text                               │        │
│  │  • "Analyze this contract. Output JSON."            │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  OUTPUT SCHEMA (enforced via tool_use/JSON mode)    │        │
│  │  {                                                  │        │
│  │    contract_type, parties, dates, payment,          │        │
│  │    clauses: [{                                      │        │
│  │      id, title, text, category, risk_score,         │        │
│  │      explanation: {tldr, what, why, consequence,    │        │
│  │                    negotiate}                        │        │
│  │    }],                                              │        │
│  │    overall_risk: {score, summary, top_risks},       │        │
│  │    summary: {executive, obligations, action_items}  │        │
│  │  }                                                  │        │
│  └─────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### Prompt Versioning

```
prompts/
├── v1/
│   ├── analysis_system.txt     -- System prompt for main analysis
│   ├── analysis_schema.json    -- Output JSON schema
│   ├── chat_system.txt         -- System prompt for chat
│   ├── comparison_system.txt   -- System prompt for comparison
│   └── examples/
│       ├── employment.json     -- Few-shot: employment contract
│       ├── nda.json            -- Few-shot: NDA
│       ├── lease.json          -- Few-shot: lease
│       ├── service.json        -- Few-shot: service agreement
│       └── freelance.json      -- Few-shot: freelance contract
└── eval/
    ├── test_contracts/         -- 50 contracts with human labels
    └── run_eval.py             -- Score prompts against test set
```

### Prompt Optimization Cycle

```
WEEK 1: Ship v1 prompts (manually crafted)
         │
         ▼
WEEK 2-4: Collect production feedback
         │
         ▼
MONTHLY:  Run eval suite on test set
         │
         ├── Accuracy dropped? → investigate failure cases
         │                        add negative examples to prompt
         │
         ├── New contract type failing? → add few-shot example
         │
         └── Users confused by explanations? → simplify language rules
                │
                ▼
          Bump prompt version, A/B test vs previous
```

---

## Pipeline Error Handling

```
┌─────────────────────────────────────────────────────────────────┐
│  ERROR RECOVERY STRATEGY                                         │
│                                                                 │
│  Stage 1 (Extraction) fails:                                    │
│  • Corrupted file → tell user, suggest re-upload                │
│  • OCR low confidence → warn user, proceed with caveat          │
│  • Password protected → tell user to remove password            │
│                                                                 │
│  Stage 2 (Segmentation) fails:                                  │
│  • No clear sections → treat entire text as one chunk           │
│  • LLM timeout → use rule-based segmentation only              │
│                                                                 │
│  Stage 3-7 (LLM Analysis) fails:                               │
│  • API timeout → retry once with exponential backoff            │
│  • Invalid JSON output → retry with stricter schema prompt      │
│  • Rate limited → queue and process later                       │
│  • Content filter → flag for manual review                      │
│                                                                 │
│  ALL STAGES: Never lose the user's document.                    │
│  Partial analysis is better than no analysis.                   │
│  If Stage 5 (risk) fails but Stage 4 worked → show             │
│  classification without risk scores, retry risk in background.  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Cost Model

```
PER-CONTRACT COST ESTIMATE:
────────────────────────────

Average contract: 15 pages, ~8,000 words, ~12,000 tokens

Stage 1 (Extract):    $0.000  (local processing)
Stage 2 (Segment):    $0.003  (Haiku, ~2K tokens I/O)
Stage 3-7 (Analysis): $0.060  (Sonnet, ~15K input + 5K output)
────────────────────────────────
Total per contract:   ~$0.063

AT SCALE:
• 1,000 contracts/day  = $63/day   = $1,890/month
• 10,000 contracts/day = $630/day  = $18,900/month

UNIT ECONOMICS:
• Individual plan ($19/month, 20 contracts) = $1.26 AI cost → 93% margin
• Professional ($49/month, 100 contracts) = $6.30 AI cost → 87% margin
```

---

## Chat Pipeline (Module 8)

```
USER QUESTION + CONTRACT TEXT + CONVERSATION HISTORY
                    │
                    ▼
┌─────────────────────────────────────────────────────────┐
│  CHAT SYSTEM PROMPT                                      │
│                                                         │
│  Role: Contract Q&A assistant                            │
│  Rules:                                                  │
│  • ONLY answer from the provided contract text           │
│  • Quote specific sections that support your answer      │
│  • If not in document, say "not covered"                │
│  • Never give legal advice                              │
│  • Distinguish "contract says" from "law says"           │
│  • Suggest follow-up questions                           │
│                                                         │
│  Context provided:                                       │
│  • Full contract text                                    │
│  • Analysis results (risk scores, classifications)       │
│  • Previous chat messages (up to 20 turns)              │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
                    STREAMING RESPONSE
                    (token by token via SSE)
```

---

## Comparison Pipeline (Module 7)

```
CONTRACT A (analyzed)  +  CONTRACT B (analyzed)
            │                       │
            └───────────┬───────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│  COMPARISON PROMPT (Claude Opus — complex reasoning)         │
│                                                             │
│  Input:                                                     │
│  • Contract A: full text + analysis JSON                    │
│  • Contract B: full text + analysis JSON                    │
│  • User context: which role are they? what do they care     │
│    about most?                                              │
│                                                             │
│  Tasks:                                                     │
│  1. Identify added/removed/modified clauses                 │
│  2. Rate significance of each change                        │
│  3. Determine which favors the user                         │
│  4. Flag subtle-but-important changes (may→shall, or→and)  │
│  5. Overall recommendation with confidence                  │
│                                                             │
│  Output: Structured comparison JSON                         │
└─────────────────────────────────────────────────────────────┘

COST: ~$0.20-0.40 per comparison (Opus, 2x contract input)
TIME: ~30-60s (acceptable — user expects comparison to take time)
```

---

## Architecture Decision Summary

| Decision | Rationale |
|----------|-----------|
| One big LLM call vs many small ones | Cheaper, faster, better cross-reference |
| Claude over open-source | 200K context, superior legal reasoning, no infra to manage |
| Zero-shot over fine-tuning | Ship faster, Claude is good enough, iterate with prompts |
| spaCy for basic NER | Free, fast, handles easy entities so LLM focuses on hard ones |
| Rule-based segmentation + LLM fix-up | Rules are free and fast for 80% of cases |
| JSON schema enforcement | Reliable structured output, no parsing failures |
| Streaming for chat | Perceived latency <2s even if full response takes 15s |
| No RAG | Contracts fit in context window — RAG adds complexity for no gain |
| No vector DB | Same reason — full document fits in prompt |

---

*End of AI Pipeline Architecture*
