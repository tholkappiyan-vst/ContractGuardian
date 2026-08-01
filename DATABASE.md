# Database Design
## ContractAI Guardian — PostgreSQL Schema

---

## Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────────┐
│    users     │──1:N──│  organizations   │──1:N──│  org_members     │
└──────┬───────┘       └────────┬─────────┘       └──────────────────┘
       │                        │
       │ 1:N                    │ 1:N
       ▼                        ▼
┌──────────────────────────────────────────┐
│              contracts                    │
│  (belongs to user OR organization)       │
└───────────────────┬──────────────────────┘
                    │
          ┌─────────┼──────────────────────────────────┐
          │ 1:N     │ 1:N                    1:1       │
          ▼         ▼                         ▼        │
┌──────────────┐ ┌──────────────┐  ┌────────────────┐ │
│  documents   │ │   clauses    │  │   analyses     │ │
└──────────────┘ └──────┬───────┘  └───────┬────────┘ │
                        │                  │          │
              ┌─────────┼─────────┐        │          │
              │ 1:N     │ 1:N     │ 1:1    │          │
              ▼         ▼         ▼        │          │
     ┌────────────┐ ┌────────┐ ┌────────┐  │          │
     │  entities  │ │ risks  │ │negotia-│  │          │
     └────────────┘ └────────┘ │ tions  │  │          │
                               └────────┘  │          │
                                           │          │
                              ┌─────────────┘          │
                              │ 1:N                    │ 1:N
                              ▼                        ▼
                    ┌──────────────────┐    ┌──────────────────┐
                    │  chat_messages   │    │   audit_logs     │
                    └──────────────────┘    └──────────────────┘
```

---

## Schema

```sql
-- ============================================================
-- EXTENSIONS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";      -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";       -- trigram search on contract text

-- ============================================================
-- TABLE 1: users
-- ============================================================

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_id        TEXT UNIQUE NOT NULL,
    email           TEXT UNIQUE NOT NULL,
    full_name       TEXT NOT NULL,
    avatar_url      TEXT,
    account_type    TEXT NOT NULL DEFAULT 'individual'
                    CHECK (account_type IN ('individual', 'corporate')),
    plan            TEXT NOT NULL DEFAULT 'free'
                    CHECK (plan IN ('free', 'individual', 'professional', 'enterprise')),
    contracts_used  INTEGER NOT NULL DEFAULT 0,
    contracts_limit INTEGER NOT NULL DEFAULT 3,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- TABLE 2: organizations
-- ============================================================

CREATE TABLE organizations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    slug            TEXT UNIQUE NOT NULL,
    owner_id        UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    plan            TEXT NOT NULL DEFAULT 'professional'
                    CHECK (plan IN ('professional', 'enterprise')),
    contracts_used  INTEGER NOT NULL DEFAULT 0,
    contracts_limit INTEGER NOT NULL DEFAULT 100,
    settings        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- TABLE 3: org_members (join table)
-- ============================================================

CREATE TABLE org_members (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            TEXT NOT NULL DEFAULT 'member'
                    CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    invited_by      UUID REFERENCES users(id),
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (org_id, user_id)
);

-- ============================================================
-- TABLE 4: contracts
-- ============================================================

CREATE TABLE contracts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id          UUID REFERENCES organizations(id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    contract_type   TEXT,                -- detected: 'employment', 'nda', 'lease', etc.
    status          TEXT NOT NULL DEFAULT 'uploaded'
                    CHECK (status IN (
                        'uploaded',       -- file received, not yet processed
                        'extracting',    -- text extraction in progress
                        'extracted',     -- text ready, analysis not started
                        'analyzing',     -- AI pipeline running
                        'analyzed',      -- complete
                        'failed'         -- pipeline error
                    )),
    error_message   TEXT,               -- populated on failure
    language        TEXT DEFAULT 'en',
    page_count      INTEGER,
    word_count      INTEGER,
    risk_score      INTEGER CHECK (risk_score BETWEEN 1 AND 10),
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    analyzed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- TABLE 5: documents (physical files)
-- ============================================================

CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id     UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    file_name       TEXT NOT NULL,
    file_type       TEXT NOT NULL CHECK (file_type IN ('pdf', 'docx', 'png', 'jpg', 'tiff')),
    file_size       BIGINT NOT NULL,     -- bytes
    storage_key     TEXT NOT NULL,        -- S3/R2 object key
    storage_bucket  TEXT NOT NULL DEFAULT 'contracts',
    raw_text        TEXT,                 -- extracted text
    ocr_used        BOOLEAN NOT NULL DEFAULT false,
    ocr_confidence  REAL,                -- 0.0-1.0
    page_count      INTEGER,
    extraction_meta JSONB DEFAULT '{}',  -- page structure, tables, headings
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- TABLE 6: clauses
-- ============================================================

CREATE TABLE clauses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id     UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    document_id     UUID REFERENCES documents(id) ON DELETE SET NULL,
    clause_index    INTEGER NOT NULL,    -- ordering within contract
    section_number  TEXT,                -- "4.1", "II.B", etc.
    title           TEXT,                -- detected or inferred heading
    body            TEXT NOT NULL,        -- clause text
    category        TEXT NOT NULL CHECK (category IN (
                        'payment', 'termination', 'liability',
                        'confidentiality', 'ip_rights', 'data_privacy',
                        'non_compete', 'warranty', 'dispute_resolution',
                        'penalties', 'force_majeure', 'assignment',
                        'governing_law', 'definitions', 'other'
                    )),
    subcategory     TEXT,                -- finer classification
    confidence      REAL NOT NULL DEFAULT 0.0 CHECK (confidence BETWEEN 0 AND 1),
    risk_score      INTEGER CHECK (risk_score BETWEEN 1 AND 10),
    is_standard     BOOLEAN,            -- standard for contract type?
    parent_id       UUID REFERENCES clauses(id) ON DELETE SET NULL,
    page_number     INTEGER,
    start_offset    INTEGER,            -- char offset in raw_text
    end_offset      INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- TABLE 7: entities
-- ============================================================

CREATE TABLE entities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id     UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    clause_id       UUID REFERENCES clauses(id) ON DELETE SET NULL,
    entity_type     TEXT NOT NULL CHECK (entity_type IN (
                        'person', 'organization', 'date', 'money',
                        'percent', 'duration', 'location',
                        'payment_term', 'penalty', 'liability_term',
                        'obligation', 'termination_condition',
                        'deadline', 'restriction'
                    )),
    value           TEXT NOT NULL,        -- canonical value
    original_text   TEXT NOT NULL,        -- as it appears in contract
    normalized      JSONB,               -- structured form, e.g. {"amount":5000,"currency":"USD"}
    confidence      REAL NOT NULL DEFAULT 0.0 CHECK (confidence BETWEEN 0 AND 1),
    role            TEXT,                -- for parties: 'employer', 'tenant', etc.
    aliases         TEXT[],              -- alternative references: {"the Company", "Employer"}
    start_offset    INTEGER,
    end_offset      INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- TABLE 8: risk_scores
-- ============================================================

CREATE TABLE risk_scores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id     UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    clause_id       UUID REFERENCES clauses(id) ON DELETE CASCADE,
    scope           TEXT NOT NULL CHECK (scope IN ('clause', 'contract', 'compounding')),
    score           INTEGER NOT NULL CHECK (score BETWEEN 1 AND 10),
    label           TEXT NOT NULL CHECK (label IN ('low', 'moderate', 'elevated', 'high', 'critical')),
    category        TEXT NOT NULL CHECK (category IN (
                        'financial_exposure', 'restrictive_terms',
                        'one_sided_obligations', 'missing_protections',
                        'unusual_language', 'compliance_risk',
                        'operational_risk'
                    )),
    explanation     TEXT NOT NULL,        -- plain-language explanation
    consequence     TEXT NOT NULL,        -- "if X happens, then Y"
    affected_party  TEXT,                -- who bears this risk
    is_standard     BOOLEAN,
    standard_note   TEXT,                -- what standard WOULD be
    related_clauses UUID[],             -- for compounding risks
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- TABLE 9: analyses (full analysis result, one per run)
-- ============================================================

CREATE TABLE analyses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id     UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    version         INTEGER NOT NULL DEFAULT 1,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'running', 'completed', 'failed')),

    -- Summary layer
    executive_summary TEXT,
    contract_type   JSONB,              -- {"type": "employment", "confidence": 0.95}
    parties         JSONB,              -- [{"name":"...", "role":"...", "type":"..."}]
    dates           JSONB,              -- {"effective":"...", "expiration":"...", ...}
    payment_summary JSONB,              -- {"total_value":"...", "schedule":[...]}
    obligations     JSONB,              -- {"you_must":[], "they_must":[]}

    -- Scores
    risk_score      INTEGER CHECK (risk_score BETWEEN 1 AND 10),
    risk_label      TEXT,
    risk_summary    TEXT,
    top_risks       JSONB DEFAULT '[]',

    -- Metadata
    model_used      TEXT,               -- 'claude-sonnet-5'
    model_version   TEXT,
    prompt_version  TEXT,               -- 'v1.3'
    tokens_input    INTEGER,
    tokens_output   INTEGER,
    cost_usd        REAL,
    processing_ms   INTEGER,            -- total pipeline time

    -- Action items
    action_items    JSONB DEFAULT '{}', -- {"negotiate":[], "verify":[], "acceptable":[]}

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

-- ============================================================
-- TABLE 10: chat_messages
-- ============================================================

CREATE TABLE chat_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id     UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT NOT NULL,
    citations       JSONB DEFAULT '[]', -- [{"clause_id":"...", "text":"quoted text"}]
    tokens_used     INTEGER,
    model_used      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- TABLE 11: negotiation_suggestions
-- ============================================================

CREATE TABLE negotiation_suggestions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id     UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    clause_id       UUID NOT NULL REFERENCES clauses(id) ON DELETE CASCADE,
    risk_score_id   UUID REFERENCES risk_scores(id) ON DELETE SET NULL,
    difficulty      TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    label           TEXT NOT NULL,       -- "Add a liability cap"
    original_text   TEXT NOT NULL,       -- the problematic clause text
    alternative_text TEXT NOT NULL,      -- suggested replacement
    explanation     TEXT NOT NULL,       -- why this is better
    talking_points  TEXT[],             -- conversation starters
    likelihood      TEXT CHECK (likelihood IN ('high', 'medium', 'low')),
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- TABLE 12: audit_logs
-- ============================================================

CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    org_id          UUID REFERENCES organizations(id) ON DELETE SET NULL,
    contract_id     UUID REFERENCES contracts(id) ON DELETE SET NULL,
    action          TEXT NOT NULL,       -- 'contract.upload', 'contract.analyze', 'contract.delete'
    resource_type   TEXT NOT NULL,       -- 'contract', 'user', 'organization'
    resource_id     UUID,
    details         JSONB DEFAULT '{}', -- action-specific payload
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Audit logs are append-only. No UPDATE or DELETE allowed at app level.
```

---

## Indexes

```sql
-- ============================================================
-- INDEXES
-- ============================================================

-- users
CREATE INDEX idx_users_clerk_id ON users(clerk_id);
CREATE INDEX idx_users_email ON users(email);

-- organizations
CREATE INDEX idx_organizations_owner ON organizations(owner_id);
CREATE INDEX idx_organizations_slug ON organizations(slug);

-- org_members
CREATE INDEX idx_org_members_user ON org_members(user_id);
CREATE INDEX idx_org_members_org ON org_members(org_id);

-- contracts (most queried table)
CREATE INDEX idx_contracts_user ON contracts(user_id);
CREATE INDEX idx_contracts_org ON contracts(org_id) WHERE org_id IS NOT NULL;
CREATE INDEX idx_contracts_status ON contracts(status);
CREATE INDEX idx_contracts_user_created ON contracts(user_id, created_at DESC);
CREATE INDEX idx_contracts_type ON contracts(contract_type) WHERE contract_type IS NOT NULL;
CREATE INDEX idx_contracts_risk ON contracts(risk_score) WHERE risk_score IS NOT NULL;

-- documents
CREATE INDEX idx_documents_contract ON documents(contract_id);
CREATE INDEX idx_documents_storage ON documents(storage_key);

-- clauses
CREATE INDEX idx_clauses_contract ON clauses(contract_id);
CREATE INDEX idx_clauses_contract_order ON clauses(contract_id, clause_index);
CREATE INDEX idx_clauses_category ON clauses(category);
CREATE INDEX idx_clauses_risk ON clauses(contract_id, risk_score DESC) WHERE risk_score IS NOT NULL;
CREATE INDEX idx_clauses_parent ON clauses(parent_id) WHERE parent_id IS NOT NULL;

-- entities
CREATE INDEX idx_entities_contract ON entities(contract_id);
CREATE INDEX idx_entities_clause ON entities(clause_id) WHERE clause_id IS NOT NULL;
CREATE INDEX idx_entities_type ON entities(contract_id, entity_type);
CREATE INDEX idx_entities_value_trgm ON entities USING gin(value gin_trgm_ops);

-- risk_scores
CREATE INDEX idx_risks_contract ON risk_scores(contract_id);
CREATE INDEX idx_risks_clause ON risk_scores(clause_id) WHERE clause_id IS NOT NULL;
CREATE INDEX idx_risks_contract_score ON risk_scores(contract_id, score DESC);
CREATE INDEX idx_risks_category ON risk_scores(category);

-- analyses
CREATE INDEX idx_analyses_contract ON analyses(contract_id);
CREATE INDEX idx_analyses_contract_version ON analyses(contract_id, version DESC);

-- chat_messages
CREATE INDEX idx_chat_contract ON chat_messages(contract_id, created_at);
CREATE INDEX idx_chat_user ON chat_messages(user_id, created_at DESC);

-- negotiation_suggestions
CREATE INDEX idx_negotiations_contract ON negotiation_suggestions(contract_id);
CREATE INDEX idx_negotiations_clause ON negotiation_suggestions(clause_id);
CREATE INDEX idx_negotiations_difficulty ON negotiation_suggestions(contract_id, difficulty);

-- audit_logs (time-series, recent first)
CREATE INDEX idx_audit_user ON audit_logs(user_id, created_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX idx_audit_org ON audit_logs(org_id, created_at DESC) WHERE org_id IS NOT NULL;
CREATE INDEX idx_audit_contract ON audit_logs(contract_id, created_at DESC) WHERE contract_id IS NOT NULL;
CREATE INDEX idx_audit_action ON audit_logs(action, created_at DESC);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);
```

---

## Relationships Summary

```
┌────────────────────────────────────────────────────────────────────┐
│  RELATIONSHIP MAP                                                   │
│                                                                    │
│  users ─────1:N────▶ contracts                                     │
│  users ─────1:N────▶ organizations (as owner)                      │
│  users ─────M:N────▶ organizations (via org_members)               │
│  users ─────1:N────▶ chat_messages                                 │
│  users ─────1:N────▶ audit_logs                                    │
│                                                                    │
│  organizations ─1:N─▶ contracts                                    │
│  organizations ─1:N─▶ org_members                                  │
│  organizations ─1:N─▶ audit_logs                                   │
│                                                                    │
│  contracts ────1:N───▶ documents                                   │
│  contracts ────1:N───▶ clauses                                     │
│  contracts ────1:N───▶ entities                                    │
│  contracts ────1:N───▶ risk_scores                                 │
│  contracts ────1:N───▶ analyses                                    │
│  contracts ────1:N───▶ chat_messages                               │
│  contracts ────1:N───▶ negotiation_suggestions                     │
│  contracts ────1:N───▶ audit_logs                                  │
│                                                                    │
│  clauses ──────1:N───▶ entities                                    │
│  clauses ──────1:N───▶ risk_scores                                 │
│  clauses ──────1:N───▶ negotiation_suggestions                     │
│  clauses ──────1:self─▶ clauses (parent-child hierarchy)           │
│                                                                    │
│  risk_scores ──1:1───▶ negotiation_suggestions (optional link)     │
│                                                                    │
│  CASCADE RULES:                                                    │
│  • Delete user → delete their contracts → cascades everything      │
│  • Delete contract → cascades all child tables                     │
│  • Delete org → contracts become user-only (SET NULL)              │
│  • Audit logs: SET NULL on user/contract delete (preserve log)     │
└────────────────────────────────────────────────────────────────────┘
```

---

## Row-Level Security (RLS)

```sql
-- ============================================================
-- ROW-LEVEL SECURITY
-- ============================================================

-- Enable RLS on all user-facing tables
ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE clauses ENABLE ROW LEVEL SECURITY;
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE negotiation_suggestions ENABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────
-- POLICY: Users see only their own contracts
-- ─────────────────────────────────────────────────────────────

CREATE POLICY contracts_user_isolation ON contracts
    USING (
        user_id = current_setting('app.current_user_id')::uuid
        OR org_id IN (
            SELECT org_id FROM org_members
            WHERE user_id = current_setting('app.current_user_id')::uuid
        )
    );

-- ─────────────────────────────────────────────────────────────
-- POLICY: Child tables inherit contract access
-- ─────────────────────────────────────────────────────────────

CREATE POLICY documents_via_contract ON documents
    USING (
        contract_id IN (
            SELECT id FROM contracts  -- inherits contracts policy
        )
    );

CREATE POLICY clauses_via_contract ON clauses
    USING (
        contract_id IN (SELECT id FROM contracts)
    );

CREATE POLICY entities_via_contract ON entities
    USING (
        contract_id IN (SELECT id FROM contracts)
    );

CREATE POLICY risks_via_contract ON risk_scores
    USING (
        contract_id IN (SELECT id FROM contracts)
    );

CREATE POLICY analyses_via_contract ON analyses
    USING (
        contract_id IN (SELECT id FROM contracts)
    );

CREATE POLICY chat_via_contract ON chat_messages
    USING (
        contract_id IN (SELECT id FROM contracts)
    );

CREATE POLICY negotiations_via_contract ON negotiation_suggestions
    USING (
        contract_id IN (SELECT id FROM contracts)
    );
```

---

## Security Considerations

```sql
-- ============================================================
-- SECURITY
-- ============================================================

-- 1. Application role (limited permissions)
CREATE ROLE app_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT DELETE ON contracts, documents, chat_messages TO app_user;
-- No DELETE on audit_logs (append-only)
REVOKE DELETE ON audit_logs FROM app_user;

-- 2. Read-only role for analytics
CREATE ROLE analytics_reader;
GRANT SELECT ON users, contracts, clauses, risk_scores, analyses TO analytics_reader;
-- No access to: documents (PII), chat_messages (PII), entities (PII)

-- 3. Sensitive column encryption (application-level)
-- These columns contain PII and are encrypted at application level:
--   documents.raw_text    → encrypted at rest (contract content)
--   documents.storage_key → encrypted (access to file)
--   entities.value        → encrypted when entity_type = 'person'
--   chat_messages.content → encrypted at rest
--
-- Implementation: AES-256-GCM encryption in application layer
-- Key management: AWS KMS / environment variable (never in DB)

-- 4. Audit log immutability
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs table is append-only';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_no_update
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

-- 5. Auto-update timestamps
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER organizations_updated_at
    BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER contracts_updated_at
    BEFORE UPDATE ON contracts FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

---

## Data Retention & Cleanup

```sql
-- ============================================================
-- DATA RETENTION
-- ============================================================

-- Soft-delete pattern for contracts (recoverable for 30 days)
ALTER TABLE contracts ADD COLUMN deleted_at TIMESTAMPTZ;

CREATE INDEX idx_contracts_deleted ON contracts(deleted_at)
    WHERE deleted_at IS NOT NULL;

-- Exclude soft-deleted from normal queries (amend RLS policy)
-- In practice: add "AND deleted_at IS NULL" to RLS policies above

-- Scheduled cleanup (run daily via cron):
-- DELETE FROM contracts WHERE deleted_at < now() - interval '30 days';
-- This cascades to documents, clauses, entities, risks, analyses, chat, negotiations

-- Audit log retention: 1 year, then archive to cold storage
-- DELETE FROM audit_logs WHERE created_at < now() - interval '1 year';

-- Chat message retention: follows contract lifecycle
-- (deleted when contract is permanently deleted)
```

---

## Common Queries (with index usage)

```sql
-- ─────────────────────────────────────────────────────────────
-- Dashboard: user's recent contracts with risk scores
-- Uses: idx_contracts_user_created
-- ─────────────────────────────────────────────────────────────
SELECT id, title, contract_type, status, risk_score, created_at
FROM contracts
WHERE user_id = $1 AND deleted_at IS NULL
ORDER BY created_at DESC
LIMIT 20;

-- ─────────────────────────────────────────────────────────────
-- Analysis view: all clauses for a contract, ordered, with risks
-- Uses: idx_clauses_contract_order, idx_risks_clause
-- ─────────────────────────────────────────────────────────────
SELECT
    c.id, c.section_number, c.title, c.body, c.category,
    c.risk_score, c.confidence,
    r.explanation, r.consequence, r.category AS risk_category
FROM clauses c
LEFT JOIN risk_scores r ON r.clause_id = c.id AND r.scope = 'clause'
WHERE c.contract_id = $1
ORDER BY c.clause_index;

-- ─────────────────────────────────────────────────────────────
-- Top risks for a contract
-- Uses: idx_risks_contract_score
-- ─────────────────────────────────────────────────────────────
SELECT id, clause_id, score, label, category, explanation, consequence
FROM risk_scores
WHERE contract_id = $1
ORDER BY score DESC
LIMIT 5;

-- ─────────────────────────────────────────────────────────────
-- All entities for a contract, grouped by type
-- Uses: idx_entities_type
-- ─────────────────────────────────────────────────────────────
SELECT entity_type, value, original_text, normalized, confidence, role
FROM entities
WHERE contract_id = $1
ORDER BY entity_type, confidence DESC;

-- ─────────────────────────────────────────────────────────────
-- Chat history for a contract
-- Uses: idx_chat_contract
-- ─────────────────────────────────────────────────────────────
SELECT role, content, citations, created_at
FROM chat_messages
WHERE contract_id = $1
ORDER BY created_at;

-- ─────────────────────────────────────────────────────────────
-- Negotiation suggestions for high-risk clauses
-- Uses: idx_negotiations_contract, idx_negotiations_difficulty
-- ─────────────────────────────────────────────────────────────
SELECT
    ns.label, ns.difficulty, ns.alternative_text,
    ns.explanation, ns.talking_points, ns.likelihood,
    c.title AS clause_title, c.body AS clause_body
FROM negotiation_suggestions ns
JOIN clauses c ON c.id = ns.clause_id
WHERE ns.contract_id = $1
ORDER BY ns.sort_order;

-- ─────────────────────────────────────────────────────────────
-- Org admin: all contracts in organization
-- Uses: idx_contracts_org
-- ─────────────────────────────────────────────────────────────
SELECT c.id, c.title, c.risk_score, c.status, u.full_name AS uploaded_by
FROM contracts c
JOIN users u ON u.id = c.user_id
WHERE c.org_id = $1 AND c.deleted_at IS NULL
ORDER BY c.created_at DESC;
```

---

## Migration Strategy

```
migrations/
├── 001_create_extensions.sql
├── 002_create_users.sql
├── 003_create_organizations.sql
├── 004_create_org_members.sql
├── 005_create_contracts.sql
├── 006_create_documents.sql
├── 007_create_clauses.sql
├── 008_create_entities.sql
├── 009_create_risk_scores.sql
├── 010_create_analyses.sql
├── 011_create_chat_messages.sql
├── 012_create_negotiation_suggestions.sql
├── 013_create_audit_logs.sql
├── 014_create_indexes.sql
├── 015_create_rls_policies.sql
├── 016_create_functions_triggers.sql
└── 017_create_roles.sql
```

Tool: **Drizzle ORM** (TypeScript schema that generates these migrations)

---

## Sizing Estimates

```
Per contract analyzed (average 15 pages):
─────────────────────────────────────────
contracts:                 1 row    (~500 bytes)
documents:                 1 row    (~50KB with raw_text)
clauses:                  15-30 rows (~2KB each = ~45KB)
entities:                 20-50 rows (~500 bytes each = ~15KB)
risk_scores:              15-30 rows (~300 bytes each = ~7KB)
analyses:                  1 row    (~10KB JSON)
negotiation_suggestions:   3-10 rows (~1KB each = ~7KB)
──────────────────────────────────────────
Total per contract:       ~135KB

At 10,000 contracts: ~1.3GB
At 100,000 contracts: ~13GB
→ Single PostgreSQL instance handles this easily through 1M contracts
```

---

*End of Database Design*
