# ContractAI Guardian

AI-powered contract analysis platform that extracts clauses, scores risks, explains decisions, and suggests negotiation improvements — all in plain language a non-lawyer can understand.

**Live:** [Frontend (Vercel)](https://contract-guardian-git-master-tholkappiyan.vercel.app) | [Backend API (Render)](https://contractguardian-nwyd.onrender.com)

---

## What It Does

Upload a PDF, DOCX, or scanned image of a contract and get:

- **Full clause extraction** with category classification
- **Risk scoring** (1-10 per clause, overall 0-100 for the contract)
- **Explainable AI** — SHAP word attribution, LIME risk factors, and LLM chain-of-thought reasoning showing *why* each clause is risky
- **Plain-language explanations** at grade-8 reading level
- **Negotiation suggestions** with alternative clause text and talking points
- **RAG-powered chat** — ask questions about your contract and get answers grounded in the document
- **Contract comparison** — diff two contracts side-by-side
- **Beginner mode** — simplified "explain like I'm 5" view

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite 5, TailwindCSS, Zustand, Recharts |
| Backend | FastAPI, Python 3.12, async SQLAlchemy 2.0, Pydantic v2 |
| AI/ML | LangChain 0.3, Google Gemini (free tier), ChromaDB, Tesseract OCR |
| Database | PostgreSQL 16 (asyncpg), Alembic migrations |
| Auth | JWT (bcrypt + python-jose) |
| Deployment | Render (backend), Vercel (frontend), Docker, Terraform (AWS) |

---

## Architecture

```
┌─────────────────┐        ┌──────────────────────────────────────┐
│   React SPA     │◄──────►│  FastAPI Backend (/api/v1)           │
│   (Vercel)      │  REST  │  ├── Auth (JWT)                      │
└─────────────────┘        │  ├── Contracts (upload/CRUD)         │
                           │  ├── Analysis (trigger/results)      │
                           │  ├── Chat (RAG Q&A)                  │
                           │  ├── Comparison (diff)               │
                           │  ├── Explainability (XAI)            │
                           │  └── Negotiation                     │
                           └──────────┬───────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                  │
              ┌─────▼─────┐   ┌──────▼──────┐   ┌──────▼──────┐
              │ PostgreSQL │   │   Gemini    │   │  ChromaDB   │
              │  (Data)    │   │   (LLM)    │   │  (Vectors)  │
              └───────────┘   └─────────────┘   └─────────────┘
```

---

## AI Pipeline

1. **Document Loading** — PyMuPDF (PDF), python-docx (DOCX), Tesseract OCR (images)
2. **Chunking & Indexing** — Custom clause-aware splitter → ChromaDB with Google embeddings
3. **Clause Extraction** — LLM identifies and categorizes each clause
4. **Risk Analysis** — Per-clause scoring with category, severity, consequence
5. **Explainability** — SHAP attribution + LIME factors + LLM reasoning chain
6. **Summary Generation** — Executive summary, parties, dates, obligations
7. **Negotiation Advice** — Alternative text for high-risk clauses (score >= 6)

---

## Project Structure

```
contractGuardproject/
├── backend/
│   ├── app/
│   │   ├── ai_engine/        # LangChain chains, prompts, RAG, evaluation
│   │   ├── api/              # Route handlers
│   │   ├── core/             # Config, DB, security, exceptions
│   │   ├── models/           # SQLAlchemy models (10 tables)
│   │   ├── schemas/          # Pydantic schemas
│   │   └── services/         # Business logic (AI, storage, audit)
│   ├── alembic/              # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/            # 13 page components
│   │   ├── components/       # Reusable UI (layout, chat, dashboard)
│   │   ├── lib/              # API client, auth store, utils
│   │   └── types/            # TypeScript interfaces
│   ├── Dockerfile
│   └── vercel.json
├── infra/terraform/          # AWS IaC (ECS, RDS, ECR)
├── docker-compose.yml        # Local dev environment
└── render.yaml               # Render.com deployment blueprint
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16
- Google Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))

### Backend

```bash
cd backend
cp .env.example .env          # Fill in DATABASE_URL, SECRET_KEY, GEMINI_API_KEY
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev
```

### Docker (full stack)

```bash
docker-compose up -d
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SECRET_KEY` | Yes | JWT signing secret |
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `GEMINI_MODEL` | No | Model name (default: `gemini-flash-latest`) |
| `REDIS_URL` | No | Redis URL (caching) |
| `CORS_ORIGINS` | No | Allowed origins (default: `http://localhost:3000`) |
| `MAX_FILE_SIZE_MB` | No | Upload limit (default: 50) |

### Frontend (`frontend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | Yes | Backend API base URL |

---

## API Endpoints

All routes under `/api/v1`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Get JWT tokens |
| GET | `/auth/me` | Current user profile |
| POST | `/contracts` | Upload contract (multipart) |
| GET | `/contracts` | List user's contracts |
| POST | `/analysis/{id}/analyze` | Trigger AI analysis |
| GET | `/analysis/{id}/results` | Get full analysis results |
| GET | `/analysis/{id}/risks` | Get risk scores |
| GET | `/analysis/{id}/clauses` | Get extracted clauses |
| GET | `/analysis/{id}/negotiations` | Get negotiation suggestions |
| POST | `/chat/{id}` | Ask a question about a contract |
| POST | `/comparison` | Compare two contracts |
| GET | `/explain/{id}/global` | Full explainability report |

---

## Deployment

### Render (current production)

Backend auto-deploys from `master` via `render.yaml`. Runs Alembic migrations on startup.

### Vercel (frontend)

Auto-deploys from `master`. SPA rewrites configured in `vercel.json`.

### AWS (Terraform)

```bash
cd infra/terraform
terraform init
terraform apply
```

Provisions ECS Fargate + RDS PostgreSQL + ECR.

---

## Workflow

```
User uploads contract
       │
       ▼
   Text extraction (PDF/DOCX/OCR)
       │
       ▼
   Chunk & index into ChromaDB
       │
       ▼
   Gemini analyzes (clauses, risks, entities, summary)
       │
       ▼
   Risk scoring engine (weighted dimensions, severity multiplier)
       │
       ▼
   Results stored in PostgreSQL
       │
       ▼
   Frontend displays: analysis, risks, chat, negotiations, explainability
```

---

## License

Private project.
