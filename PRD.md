# Product Requirements Document
## ContractAI Guardian

**Version:** 1.0  
**Date:** 2026-08-01  
**Status:** Draft  

---

## 1. Product Overview

**Product:** ContractAI Guardian  
**Purpose:** AI-powered contract analysis platform that enables companies and individuals without legal expertise to upload contracts, understand risks, and negotiate better terms before signing.

**Target Users:**
- Individuals signing leases, employment contracts, freelance agreements, NDAs
- Small businesses without in-house legal teams
- Corporate legal teams seeking faster first-pass review

**Core Value Proposition:** Upload a contract, get a plain-language risk analysis in under 60 seconds.

---

## 2. Module Specifications

---

### MODULE 1: Contract Upload System

**Purpose:** Accept contracts in any common format and extract clean text for analysis.

#### Supported Formats

| Format | Method | Max Size |
|--------|--------|----------|
| PDF (text-based) | pdf-parse extraction | 50MB |
| PDF (scanned/image) | OCR pipeline | 50MB |
| DOCX | mammoth conversion | 50MB |
| Images (JPG, PNG, TIFF) | OCR pipeline | 20MB per image |

#### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| UP-1 | Single file upload via drag-and-drop or file picker | P0 |
| UP-2 | Multiple file upload (up to 10 files per batch) | P0 |
| UP-3 | Automatic format detection from file extension + MIME type | P0 |
| UP-4 | PDF text extraction for text-based PDFs | P0 |
| UP-5 | OCR for scanned PDFs and images (Tesseract or cloud OCR) | P0 |
| UP-6 | DOCX parsing preserving structure (headings, lists, tables) | P0 |
| UP-7 | Upload progress indicator per file | P0 |
| UP-8 | File validation: reject corrupted, empty, or password-protected files with clear error | P0 |
| UP-9 | Automatic language detection of extracted text | P1 |
| UP-10 | Page/section structure preservation in extracted text | P1 |
| UP-11 | Table extraction from PDFs (maintain row/column structure) | P1 |
| UP-12 | Batch status view: show processing state per file in multi-upload | P0 |

#### OCR Pipeline

```
Image/Scanned PDF
      │
      ▼
 Preprocessing (deskew, contrast, noise removal)
      │
      ▼
 OCR Engine (Tesseract 5 / Google Vision API fallback)
      │
      ▼
 Post-processing (spelling correction, layout reconstruction)
      │
      ▼
 Clean text output
```

#### Upload Flow

```
User selects file(s)
      │
      ▼
Client-side validation (type, size)
      │
      ▼
Upload to object storage (presigned URL)
      │
      ▼
Server receives upload notification
      │
      ▼
Text extraction job triggered
      │
      ▼
Status → "processing"
      │
      ▼
Text extracted → status → "ready"
      │
      ▼
Analysis can begin (auto or manual trigger)
```

#### Acceptance Criteria
- PDF text extraction accuracy: >99% for text-based PDFs
- OCR accuracy: >95% for clean scans, >85% for photos of documents
- Upload-to-ready time: <10s for text PDFs, <30s for OCR
- Graceful failure: corrupted files don't crash the pipeline, user gets actionable error

---

### MODULE 2: Contract Understanding Engine

**Purpose:** Extract structured data from unstructured contract text. This is the foundational analysis that all other modules build upon.

#### Extraction Targets

| ID | Data Point | Output Type | Example |
|----|-----------|-------------|---------|
| EX-1 | Contract type | Enum + confidence | "Employment Agreement" (0.95) |
| EX-2 | Parties | Array of {name, role} | [{name: "Acme Corp", role: "employer"}, {name: "Jane Doe", role: "employee"}] |
| EX-3 | Effective date | ISO date | "2026-09-01" |
| EX-4 | Expiration date | ISO date or "indefinite" | "2027-08-31" |
| EX-5 | Renewal terms | Structured text | "Auto-renews for 1-year terms unless 30-day written notice" |
| EX-6 | Payment terms | Structured object | {amount, currency, frequency, due_date, method} |
| EX-7 | Penalties | Array of {trigger, consequence, amount} | [{trigger: "late payment", consequence: "interest", amount: "1.5% monthly"}] |
| EX-8 | Liabilities | Array of {party, scope, cap, exclusions} | [{party: "contractor", scope: "direct damages", cap: "contract value"}] |
| EX-9 | Termination conditions | Array of {trigger, notice_period, consequences} | [{trigger: "breach", notice_period: "30 days", consequences: "..."}] |
| EX-10 | Obligations | Array of {party, obligation, deadline, consequence_of_breach} | [{party: "tenant", obligation: "maintain property", deadline: "ongoing"}] |
| EX-11 | Clauses (full list) | Array of {id, title, text, category} | See Module 3 |

#### Contract Types Recognized

- Employment Agreement
- Non-Disclosure Agreement (NDA)
- Service Agreement / SaaS Terms
- Lease / Rental Agreement
- Freelance / Independent Contractor Agreement
- Partnership Agreement
- Purchase Agreement
- Licensing Agreement
- Loan Agreement
- Settlement Agreement
- Terms of Service
- Other (with AI-generated label)

#### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| UE-1 | Identify contract type with confidence score | P0 |
| UE-2 | Extract all parties with their roles | P0 |
| UE-3 | Extract all dates (effective, expiration, renewal, deadlines) | P0 |
| UE-4 | Extract payment information (amounts, schedules, conditions) | P0 |
| UE-5 | Extract penalty clauses with triggers and consequences | P0 |
| UE-6 | Extract liability terms including caps and exclusions | P0 |
| UE-7 | Extract termination conditions and notice requirements | P0 |
| UE-8 | Extract obligations per party with deadlines | P0 |
| UE-9 | Handle multi-party contracts (>2 parties) | P1 |
| UE-10 | Cross-reference extracted data (e.g., payment date vs termination for non-payment) | P1 |
| UE-11 | Flag missing standard elements (e.g., no termination clause in a 3-year contract) | P1 |
| UE-12 | Confidence scores on all extractions | P1 |

#### Output Schema

```json
{
  "contract_type": { "type": "string", "confidence": 0.95 },
  "parties": [
    { "name": "string", "role": "string", "type": "individual|corporate" }
  ],
  "dates": {
    "effective": "ISO date",
    "expiration": "ISO date | null",
    "renewal": { "type": "auto|manual|none", "terms": "string" },
    "key_deadlines": [{ "date": "ISO date", "description": "string" }]
  },
  "payment": {
    "total_value": { "amount": "number", "currency": "string" },
    "schedule": [{ "amount": "number", "due": "string", "condition": "string" }],
    "late_payment": { "penalty": "string", "grace_period": "string" }
  },
  "penalties": [
    { "trigger": "string", "consequence": "string", "amount": "string|null", "clause_ref": "string" }
  ],
  "liabilities": [
    { "party": "string", "scope": "string", "cap": "string|null", "exclusions": ["string"] }
  ],
  "termination": [
    { "type": "for_cause|convenience|mutual|expiration", "trigger": "string", "notice_period": "string", "consequences": "string" }
  ],
  "obligations": [
    { "party": "string", "obligation": "string", "deadline": "string", "breach_consequence": "string" }
  ]
}
```

#### Acceptance Criteria
- Extraction accuracy: >90% F1 score across all fields on test set of 100 contracts
- Contract type identification: >95% accuracy
- Party extraction: >98% accuracy
- Date extraction: >95% accuracy
- Processing time: <45s for contracts under 20 pages

---

### MODULE 3: Clause Intelligence

**Purpose:** Segment the contract into individual clauses, classify each by category, and enable targeted analysis per clause.

#### Clause Categories

| Category | Description | Common Indicators |
|----------|-------------|-------------------|
| Payment | Financial obligations, pricing, invoicing | "shall pay", "compensation", "fees", "invoice" |
| Liability | Responsibility limits, indemnification | "liable", "indemnify", "hold harmless", "damages" |
| Confidentiality | Information protection, NDA terms | "confidential", "proprietary", "disclose", "trade secret" |
| Termination | Contract ending conditions | "terminate", "cancel", "expiration", "notice period" |
| Intellectual Property | IP ownership, licensing, work product | "intellectual property", "ownership", "license", "work product" |
| Data Privacy | Data handling, GDPR, processing | "personal data", "data protection", "GDPR", "processing" |
| Non-compete | Competition restrictions | "non-compete", "restrict", "competing business", "solicit" |
| Warranty | Guarantees, representations | "warrants", "represents", "guarantee", "as-is" |
| Dispute Resolution | Conflict handling, jurisdiction | "arbitration", "mediation", "governing law", "jurisdiction" |
| Penalties | Breach consequences, liquidated damages | "penalty", "liquidated damages", "breach", "forfeit" |
| Force Majeure | Uncontrollable events | "force majeure", "act of god", "beyond control" |
| Assignment | Transfer of rights/obligations | "assign", "transfer", "successor" |
| Governing Law | Jurisdiction and applicable law | "governed by", "laws of", "jurisdiction" |
| Other | Uncategorized or boilerplate | Miscellaneous |

#### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| CI-1 | Segment contract text into individual clauses by section/paragraph | P0 |
| CI-2 | Classify each clause into one or more categories | P0 |
| CI-3 | Assign confidence score to classification | P0 |
| CI-4 | Handle multi-category clauses (e.g., a clause covering both payment and penalty) | P0 |
| CI-5 | Preserve original clause text alongside classification | P0 |
| CI-6 | Generate clause-level summary (1-2 sentences) | P0 |
| CI-7 | Identify standard vs. non-standard clauses (flag unusual language) | P1 |
| CI-8 | Detect missing expected clauses for contract type | P1 |
| CI-9 | Cross-reference related clauses (e.g., termination clause referencing penalty clause) | P2 |

#### Output Schema (per clause)

```json
{
  "id": "clause_001",
  "title": "Payment Terms",
  "original_text": "The Client shall pay...",
  "categories": [
    { "category": "payment", "confidence": 0.92 },
    { "category": "penalties", "confidence": 0.45 }
  ],
  "summary": "Client pays $5,000 monthly by the 15th, with 5% late fee after 10-day grace period.",
  "is_standard": true,
  "related_clauses": ["clause_007"],
  "section_number": "4.1"
}
```

#### Acceptance Criteria
- Clause segmentation: correctly identifies >95% of clause boundaries
- Primary category classification accuracy: >90%
- No clause lost during segmentation (100% text coverage)
- Processing time: included in Module 2 pipeline, no additional latency

---

### MODULE 4: Risk Analysis

**Purpose:** Score risk at clause and contract level, explain what could go wrong, and prioritize what the user should focus on.

#### Risk Scoring Model

**Clause-Level Risk Score: 1-10**

| Score | Label | Meaning |
|-------|-------|---------|
| 1-2 | Low | Standard, fair terms. No action needed. |
| 3-4 | Moderate | Slightly one-sided but common. Worth noting. |
| 5-6 | Elevated | Meaningfully unfavorable. Should understand implications. |
| 7-8 | High | Significantly risky. Negotiate before signing. |
| 9-10 | Critical | Dangerous terms. Do not sign without legal review or major changes. |

**Contract-Level Risk Score: 1-10**
- Weighted average of clause risks
- Weights: critical clauses (liability, termination, penalties) count 2x
- Adjusted upward if multiple high-risk clauses compound each other

#### Risk Categories

| Category | Example |
|----------|---------|
| Financial Exposure | Unlimited liability, penalty clauses without caps |
| Restrictive Terms | Non-compete >2 years, broad IP assignment |
| One-sided Obligations | Only one party has termination rights |
| Missing Protections | No liability cap, no dispute resolution |
| Unusual Language | Non-standard phrasing that obscures meaning |
| Compliance Risk | GDPR violations, illegal non-compete scope |
| Operational Risk | Impossible delivery timelines, ambiguous scope |

#### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| RA-1 | Generate risk score (1-10) for each classified clause | P0 |
| RA-2 | Generate overall contract risk score (1-10) | P0 |
| RA-3 | Assign risk category to each flagged risk | P0 |
| RA-4 | Generate plain-language risk explanation per clause | P0 |
| RA-5 | Generate "possible consequences" — what could actually happen | P0 |
| RA-6 | Identify the top 3 risks and highlight them prominently | P0 |
| RA-7 | Detect compounding risks (multiple clauses that together create higher risk) | P1 |
| RA-8 | Benchmark risk against "standard" for contract type (e.g., "this NDA is stricter than typical") | P1 |
| RA-9 | Distinguish risks for each party (what's risky for YOU vs. the other side) | P1 |
| RA-10 | Flag missing clauses that would normally protect the user | P1 |

#### Output Schema

```json
{
  "contract_risk_score": 7,
  "contract_risk_label": "High",
  "risk_summary": "This contract has significantly one-sided liability terms and an unusually broad non-compete clause.",
  "top_risks": [
    {
      "rank": 1,
      "clause_id": "clause_012",
      "category": "financial_exposure",
      "score": 9,
      "title": "Unlimited Personal Liability",
      "explanation": "You are personally liable for any damages with no cap.",
      "consequences": "If anything goes wrong, the other party can sue you for unlimited amounts — your personal assets are at risk.",
      "affected_party": "you"
    }
  ],
  "clause_risks": [
    {
      "clause_id": "clause_001",
      "score": 3,
      "label": "Moderate",
      "category": "financial_exposure",
      "explanation": "...",
      "consequences": "..."
    }
  ],
  "missing_protections": [
    {
      "expected_clause": "Liability Cap",
      "why_it_matters": "Without a cap, your exposure is theoretically unlimited.",
      "recommendation": "Add a clause limiting liability to the total contract value."
    }
  ],
  "compounding_risks": [
    {
      "clauses": ["clause_012", "clause_015"],
      "explanation": "The unlimited liability clause combined with the broad definition of 'damages' means..."
    }
  ]
}
```

#### Risk Visualization

```
Contract Risk Score:  ████████░░ 7/10 HIGH

Top Risks:
┌─────────────────────────────────────────────┐
│ 🔴 CRITICAL: Unlimited Personal Liability   │
│    Clause 12 — Liability                    │
│    You could lose personal assets.          │
├─────────────────────────────────────────────┤
│ 🟠 HIGH: 3-year Non-compete                │
│    Clause 8 — Non-compete                   │
│    You cannot work in this industry.        │
├─────────────────────────────────────────────┤
│ 🟡 ELEVATED: Auto-renewal without notice    │
│    Clause 3 — Termination                   │
│    Contract renews unless you cancel 90     │
│    days early.                              │
└─────────────────────────────────────────────┘
```

#### Acceptance Criteria
- Risk scores align with human legal review >85% of the time (within 2 points)
- Zero false negatives on critical risks (9-10) in test set
- Every risk has a non-generic explanation and concrete consequence
- Processing time: included in Module 2 pipeline, <60s total

---

### MODULE 5: Non-Lawyer Explanation Mode

**Purpose:** Translate every piece of analysis into language a non-lawyer can understand and act on. This is not a separate feature — it's the default output mode for individual users.

#### Explanation Framework

Every clause explanation answers four questions:

| Question | Purpose | Example Output |
|----------|---------|----------------|
| "What does this mean?" | Plain translation of legal language | "This says if you quit within 2 years, you have to pay back your signing bonus — all of it, not prorated." |
| "Why should I care?" | Personal relevance and stakes | "If you get a better offer in 18 months, you'd owe $15,000 to leave." |
| "What can happen?" | Concrete worst-case scenario | "They could deduct it from your final paycheck or sue you for the full amount." |
| "What should I negotiate?" | Actionable next step | "Ask for a prorated repayment schedule — after 1 year, you'd only owe 50%." |

#### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NL-1 | Generate 4-question explanation for every flagged clause | P0 |
| NL-2 | Use no legal jargon in explanations (reading level: grade 8) | P0 |
| NL-3 | Use concrete examples with actual numbers from the contract | P0 |
| NL-4 | Adapt tone to contract type (employment → "your boss", lease → "your landlord") | P0 |
| NL-5 | Provide "TL;DR" one-line summary at top of each clause explanation | P0 |
| NL-6 | Highlight action items separately from explanations | P1 |
| NL-7 | Offer "explain more" drill-down for complex clauses | P1 |
| NL-8 | Support multiple languages (respond in user's detected/selected language) | P2 |

#### Tone Guidelines

**Do:**
- Use "you" and "they" — make it personal
- Use concrete scenarios: "If you miss a payment by even one day..."
- Use analogies for complex concepts: "This is like signing a blank check — they decide the amount later"
- Be direct about consequences: "You could lose your deposit"

**Don't:**
- Use legal terms without immediate explanation
- Be vague: "This could have implications" (say WHAT implications)
- Hedge unnecessarily: "This might perhaps potentially..." (be clear)
- Assume prior knowledge of contract law

#### Output Example

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Clause 7: Non-Compete Agreement
  TL;DR: You can't work for a competitor for 2 years after leaving.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ORIGINAL:
  "Employee agrees that for a period of twenty-four (24) months
  following termination of employment for any reason, Employee
  shall not directly or indirectly engage in, consult for, or
  be employed by any business that competes with Company within
  a 50-mile radius..."

  ─────────────────────────────────────────

  WHAT DOES THIS MEAN?
  After you leave this job — whether you quit or get fired — you
  cannot work for any competitor within 50 miles for 2 full years.
  "Indirectly" means you also can't consult or freelance for them.

  WHY SHOULD I CARE?
  2 years is a long time to be locked out of your industry. If most
  companies in your field are within 50 miles, you'd essentially
  need to change careers or relocate to keep working.

  WHAT CAN HAPPEN?
  If you take a competing job, they can sue you. Courts sometimes
  enforce these — you could be forced to leave your new job AND
  pay damages. In [state], non-competes are [enforceable/limited/
  unenforceable].

  WHAT SHOULD I NEGOTIATE?
  • Reduce to 6-12 months (industry standard)
  • Narrow the definition of "competitor"
  • Add a carve-out: only applies if you leave voluntarily
  • Ask for compensation during the non-compete period

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### Acceptance Criteria
- Flesch-Kincaid readability score of explanations: grade 8 or below
- Every explanation uses at least one concrete number/date from the actual contract
- User comprehension test: >90% of test users correctly identify the risk after reading
- No clause left unexplained in the final output

---

### MODULE 6: Negotiation Assistant

**Purpose:** Don't just tell users what's wrong — tell them exactly what to say back. Generate specific alternative language and talking points they can use in negotiation.

#### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NA-1 | For every high-risk clause (score >=7), generate alternative wording | P0 |
| NA-2 | Provide 2-3 negotiation points per risky clause | P0 |
| NA-3 | Alternative wording must be legally coherent (not just "remove this clause") | P0 |
| NA-4 | Rank suggestions by likelihood of acceptance (easy ask → hard ask) | P1 |
| NA-5 | Provide explanation of WHY the alternative is better | P0 |
| NA-6 | Generate a "negotiation email/message" draft the user can send | P1 |
| NA-7 | Adapt suggestions to power dynamic (employee vs. employer, tenant vs. landlord) | P1 |
| NA-8 | Flag clauses that are non-negotiable in practice (boilerplate in standard terms) | P1 |

#### Output Schema

```json
{
  "clause_id": "clause_012",
  "original_text": "Contractor shall be liable for all damages...",
  "risk_score": 9,
  "negotiation": {
    "why_this_is_bad": "You're accepting unlimited financial liability for any problem, even ones that aren't your fault.",
    "suggestions": [
      {
        "difficulty": "easy",
        "label": "Add a liability cap",
        "alternative_text": "Contractor's total liability under this agreement shall not exceed the total fees paid under this agreement in the preceding 12-month period.",
        "why_better": "Limits your maximum exposure to what you were actually paid. Industry standard.",
        "likelihood_accepted": "high"
      },
      {
        "difficulty": "medium",
        "label": "Exclude indirect damages",
        "alternative_text": "In no event shall either party be liable for indirect, incidental, consequential, or punitive damages.",
        "why_better": "Removes open-ended 'butterfly effect' liability. Very standard in tech contracts.",
        "likelihood_accepted": "medium"
      },
      {
        "difficulty": "hard",
        "label": "Mutual liability",
        "alternative_text": "Each party's liability shall be limited to direct damages not exceeding the fees paid in the prior 12 months. Neither party shall be liable for indirect or consequential damages.",
        "why_better": "Makes it fair — they have the same limits you do.",
        "likelihood_accepted": "medium"
      }
    ],
    "talking_points": [
      "Unlimited liability is unusual for a contract of this size. Industry standard is a cap at 12 months of fees.",
      "I'm happy to take responsibility for my direct work, but open-ended liability for consequential damages isn't something I can accept.",
      "Can we add mutual limitations? That protects both sides equally."
    ],
    "draft_response": "Hi [Name],\n\nI've reviewed the agreement and I'm excited to move forward. I'd like to discuss one adjustment to Section 12 (Liability):\n\nThe current unlimited liability clause is broader than industry standard. I'd propose limiting each party's liability to direct damages, capped at fees paid in the preceding 12 months. This is mutual and protects both sides.\n\nWould you be open to this adjustment? Happy to discuss.\n\nBest,\n[Your name]"
  }
}
```

#### Acceptance Criteria
- Alternative wording is syntactically valid contract language (not informal paraphrasing)
- Every suggestion includes difficulty rating and explanation
- Talking points are conversational, not legal-sounding
- Draft response is ready to send with minimal editing

---

### MODULE 7: Contract Comparison

**Purpose:** Compare two contracts side-by-side to identify differences, determine which is more favorable, and highlight changes between versions.

#### Use Cases

1. **Version comparison:** "My landlord sent a revised lease — what changed?"
2. **Option comparison:** "I have two job offers — which contract is better?"
3. **Standard comparison:** "How does this NDA compare to a typical one?"

#### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| CC-1 | Accept two uploaded contracts for comparison | P0 |
| CC-2 | Identify added, removed, and modified clauses between documents | P0 |
| CC-3 | Generate overall "which is better for you" recommendation with reasoning | P0 |
| CC-4 | Side-by-side risk score comparison | P0 |
| CC-5 | Clause-by-clause diff with significance rating | P0 |
| CC-6 | Highlight changes that affect user's rights/obligations | P0 |
| CC-7 | Flag changes that LOOK minor but ARE significant (e.g., "may" → "shall") | P1 |
| CC-8 | Compare against "standard" template for contract type (AI-generated baseline) | P2 |
| CC-9 | Support comparison of contracts in different formats (PDF vs DOCX) | P0 |

#### Output Schema

```json
{
  "comparison_summary": "Contract B is significantly more favorable. It adds a liability cap, shortens the non-compete, and clarifies termination rights.",
  "recommendation": "B",
  "confidence": 0.88,
  "risk_comparison": {
    "contract_a": { "score": 7, "label": "High" },
    "contract_b": { "score": 4, "label": "Moderate" }
  },
  "differences": [
    {
      "category": "liability",
      "significance": "critical",
      "contract_a": "Unlimited liability for all damages",
      "contract_b": "Liability capped at 12 months of fees",
      "impact": "Your maximum financial exposure drops from unlimited to ~$60,000",
      "favors": "B"
    },
    {
      "category": "termination",
      "significance": "minor",
      "contract_a": "30-day notice to terminate",
      "contract_b": "45-day notice to terminate",
      "impact": "You need to give 2 weeks more notice before leaving",
      "favors": "A"
    }
  ],
  "unchanged": ["payment_terms", "confidentiality", "ip_ownership"],
  "subtle_changes": [
    {
      "clause": "Section 5.2",
      "change": "'may terminate' changed to 'shall terminate'",
      "significance": "Changes discretionary termination to mandatory — they MUST terminate if condition is met, removing their flexibility (which could benefit or harm you depending on context)."
    }
  ]
}
```

#### Comparison View (UI)

```
┌─────────────────────┬─────────────────────┐
│   CONTRACT A        │   CONTRACT B        │
│   Risk: 7/10 HIGH   │   Risk: 4/10 MOD    │
├─────────────────────┼─────────────────────┤
│                     │                     │
│  § Liability        │  § Liability        │
│  "...all damages    │  "...capped at 12   │
│  without limit..."  │  months of fees..." │
│  ⚠️ CRITICAL RISK   │  ✓ Standard term    │
│                     │                     │
├─────────────────────┼─────────────────────┤
│ VERDICT: Contract B is significantly      │
│ better for you. Key improvement:          │
│ liability cap added.                      │
└───────────────────────────────────────────┘
```

#### Acceptance Criteria
- Correctly identifies >95% of meaningful differences between two contracts
- "Which is better" recommendation matches human legal assessment >85% of the time
- Subtle-but-significant changes (may→shall, or→and) are caught and flagged
- Comparison completes in <90s for two 20-page contracts

---

### MODULE 8: AI Contract Chat

**Purpose:** Let users ask natural language questions about their uploaded contract and get answers grounded exclusively in the document content.

#### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| CH-1 | Accept natural language questions about an uploaded contract | P0 |
| CH-2 | Answer ONLY from the uploaded document — never hallucinate or use general knowledge | P0 |
| CH-3 | Quote the specific clause(s) that support the answer | P0 |
| CH-4 | Say "this contract doesn't address that" when the answer isn't in the document | P0 |
| CH-5 | Maintain conversation context (follow-up questions work) | P0 |
| CH-6 | Support questions in plain language ("Can I quit?", "What if I'm late?") | P0 |
| CH-7 | Distinguish between what the contract SAYS and what the LAW says (only answer the former) | P0 |
| CH-8 | Provide confidence indicator on answers | P1 |
| CH-9 | Suggest follow-up questions after each answer | P1 |
| CH-10 | Support questions that span multiple clauses ("What are ALL my obligations?") | P0 |
| CH-11 | Remember user context within session ("you mentioned earlier...") | P1 |

#### Grounding Rules

The AI MUST:
- Only reference content from the uploaded document
- Quote specific sections when answering
- Clearly state when something is not covered in the contract
- Distinguish between "the contract says X" and "typically in contracts like this, X" (only do the former)
- Never provide legal advice — frame as "based on this document" not "you should"

The AI MUST NOT:
- Invent clauses that don't exist
- Answer questions about law/regulations (only about this specific contract)
- Make assumptions about implied terms not in the document
- Provide definitive legal interpretation (flag ambiguous language as ambiguous)

#### Example Interactions

```
USER: Can I terminate this contract early?

ASSISTANT: Based on Section 8.2 of your contract, yes — but with conditions:

"Either party may terminate this agreement with 60 days' written
notice, provided all outstanding payments are settled."

So you can leave early if:
1. You give 60 days' written notice (email likely counts — see Section 14 on notices)
2. You've paid everything you owe up to that point

⚠️ Note: Section 8.3 adds that if YOU terminate early (not them),
you forfeit the security deposit ($3,000). This is separate from
outstanding payments.

Want me to explain the notice requirements in more detail?
```

```
USER: What happens if I don't pay on time?

ASSISTANT: Your contract has two consequences for late payment (Section 4.3):

1. **Late fee:** "A penalty of 1.5% per month shall accrue on any
   balance outstanding beyond 10 days past due."
   → That's 18% per year compounding.

2. **Termination trigger:** Section 8.1(c) says: "Provider may
   terminate immediately upon 30 days of non-payment."
   → If you don't pay for 30 days, they can end the contract
   AND you'd still owe everything accrued.

The contract does NOT mention a grace period beyond the 10 days.

Related: Should I check what happens to your work/deliverables if they terminate for non-payment?
```

```
USER: Does this contract say anything about remote work?

ASSISTANT: No — this contract does not contain any provisions about
remote work, work location, or workplace flexibility.

This means the topic is either:
- Governed by a separate policy not included here, or
- Left to the employer's discretion (they could require in-office)

If remote work is important to you, you may want to request it be
added explicitly. Want me to suggest clause language for that?
```

#### Chat UI Requirements

- Streaming responses (token-by-token display)
- Persistent chat history per contract (survives page refresh)
- "Copy answer" button per response
- Clause references are clickable (scroll to clause in analysis view)
- Suggested questions shown when chat is empty (based on contract type)
- Clear visual separation between quoted contract text and AI explanation

#### Acceptance Criteria
- Answers are grounded in document: 0% hallucination rate on test set
- "Not found" answers are correct: doesn't say "not covered" when it IS covered
- Response time: first token in <2s (streaming)
- Conversation context maintained for at least 20 turns
- Handles ambiguous contract language by flagging ambiguity, not guessing

---

## 3. Non-Functional Requirements

### Performance

| Metric | Target |
|--------|--------|
| Upload + text extraction | <10s (text PDF), <30s (OCR) |
| Full analysis pipeline | <60s for contracts under 20 pages |
| Chat response (first token) | <2s |
| Page load time | <2s |
| Concurrent users supported | 100 (phase 1), 1000 (phase 2) |

### Security

| Requirement | Implementation |
|-------------|---------------|
| Data encryption at rest | AES-256 (storage provider default) |
| Data encryption in transit | TLS 1.3 |
| Document isolation | Users can only access their own contracts |
| Data retention | User-configurable, default 90 days, permanent delete on request |
| No training on user data | Contracts never used for model training (Claude API guarantee) |
| Auth | Clerk (OAuth, MFA support) |
| Rate limiting | 10 contracts/hour (free), 100/hour (paid) |

### Reliability

| Metric | Target |
|--------|--------|
| Uptime | 99.5% (phase 1), 99.9% (phase 2) |
| Data durability | 99.999% (S3/R2 standard) |
| Analysis success rate | >98% (graceful failure with retry for the rest) |
| Error recovery | Failed analyses auto-retry once, then notify user |

### Compliance

| Requirement | Notes |
|-------------|-------|
| GDPR | Data deletion, export, consent management |
| SOC 2 | Phase 3 (when targeting enterprise) |
| No legal advice disclaimer | Prominently displayed — "This is not legal advice" |

---

## 4. User Flows

### Flow 1: Individual User — First Contract

```
Landing page → Sign up (Clerk) → Upload contract → Wait for analysis (~30s)
    → View risk score + summary → Read clause explanations → Ask follow-up
    questions in chat → Export analysis as PDF (optional)
```

### Flow 2: Corporate User — Batch Review

```
Dashboard → Batch upload (up to 10) → View processing status
    → Click into each analysis → Compare two contracts → Share analysis
    with team member → Export report
```

### Flow 3: Returning User — New Version

```
Dashboard → Upload revised contract → Select "Compare with previous"
    → Choose original → View diff + risk comparison → Check if concerns
    were addressed → Ask chat "did they fix the liability issue?"
```

---

## 5. Success Metrics

| Metric | Target (3 months post-launch) |
|--------|-------------------------------|
| Contracts analyzed | 10,000 |
| User retention (30-day) | 40% |
| Analysis accuracy (user feedback) | >4.2/5 stars |
| Time to value (upload → insight) | <90 seconds |
| Conversion free → paid | 5% |
| NPS | >50 |

---

## 6. Monetization Model

| Tier | Price | Includes |
|------|-------|----------|
| Free | $0 | 3 contracts/month, basic analysis, no comparison |
| Individual | $19/month | 20 contracts/month, full analysis, comparison, chat |
| Professional | $49/month | 100 contracts/month, batch upload, priority processing, export |
| Enterprise | Custom | Unlimited, API access, team features, SSO, custom prompts |

---

## 7. Constraints and Assumptions

**Constraints:**
- Claude API context window (200K tokens) limits single-pass analysis to ~150 pages
- OCR accuracy depends on scan quality — degraded handwritten text not supported
- LLM analysis is non-deterministic — same contract may get slightly different scores on re-analysis
- Not legal advice — must be clearly disclaimed, cannot replace attorney review for high-stakes contracts

**Assumptions:**
- Most user contracts are <30 pages (covers 95% of individual use cases)
- English-language contracts are phase 1 priority
- Users accept ~60s processing time for a thorough analysis
- LLM quality for contract analysis is sufficient (validated by prototype testing)

---

## 8. Out of Scope (Phase 1)

- E-signature integration
- Contract template generation from scratch
- Legal database / case law research
- Regulatory compliance checking (GDPR audit, etc.)
- Contract lifecycle management (tracking renewals, deadlines)
- Mobile native apps
- On-premise deployment
- Real-time collaborative editing
- Integration with document management systems (SharePoint, Google Drive)

---

## 9. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM hallucination in analysis | Users trust incorrect risk assessment | Grounding rules, confidence scores, "verify with lawyer" disclaimer |
| Claude API downtime | Users can't analyze contracts | Queue uploads, process when API returns; add fallback provider in phase 2 |
| Low OCR quality for poor scans | Incomplete analysis | Detect low-confidence OCR, warn user, suggest re-upload of better scan |
| Legal liability from "advice" | Company sued for bad analysis | Strong disclaimers, never say "you should" — only "this contract says" |
| Data breach of sensitive contracts | Loss of trust, legal exposure | Encryption, isolation, short retention, SOC 2 (phase 3) |
| Cost overrun from LLM API calls | Unsustainable unit economics | Token tracking per analysis, cost caps, cache common clause patterns |

---

*End of PRD v1.0*
