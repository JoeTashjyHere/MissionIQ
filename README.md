# MissionIQ

**MissionIQ** is a secure Operational Intelligence Platform that helps organizations win, deliver, and improve mission-critical work. It transforms contracts, documents, processes, organizational knowledge, and operational data into actionable intelligence.

This repository contains the MVP foundation, focused on the first module: **Capture Intelligence**. The platform architecture is designed from day one to host the full module suite (Capture · Operations · Process · Performance · Risk · Organizational · Market) on a single intelligence core.

---

## Product Architecture

```
MissionIQ
├── Capture Intelligence       (Win)         ← MVP module group
├── Operations Intelligence    (Deliver)     ← stubbed
├── Process Intelligence       (Improve)     ← stubbed
├── Performance Intelligence                 ← stubbed
├── Risk Intelligence                        ← stubbed
├── Organizational Intelligence              ← stubbed
└── Market Intelligence                      ← stubbed (SAM.gov client live)
```

> Users are always inside **MissionIQ**. Capture Intelligence is a module *within* MissionIQ, never a separate product.

---

## Architecture Documents

Read these in order before contributing:

1. [System Architecture](docs/architecture/01-system-architecture.md)
2. [Folder Structure](docs/architecture/02-folder-structure.md)
3. [Database Schema](docs/architecture/03-database-schema.md)
4. [API Design](docs/architecture/04-api-design.md)
5. [UI Design System](docs/architecture/05-ui-design-system.md)
6. [Security Architecture](docs/architecture/06-security-architecture.md)
7. [Implementation Roadmap](docs/architecture/07-implementation-roadmap.md)

---

## Quick Start (Docker)

Requires Docker Desktop (or Colima) and ~4 GB free RAM.

```bash
git clone <repo>
cd MissionIQ

cp .env.example .env
# Edit .env if you want to plug in real LLM keys. The default config uses
# the deterministic `local_stub` LLM so the whole pipeline works offline.

docker compose up --build
```

When healthy:
- Frontend: http://localhost:3000
- Backend:  http://localhost:8000 (OpenAPI docs at `/docs`)
- Postgres: localhost:5432

The backend container auto-runs Alembic migrations and a seed script that creates a demo workspace, a demo user, an example opportunity, and ingests an example RFP.

Demo credentials (created by the seed):
```
email:    demo@missioniq.dev
password: MissionIQ!Demo2026
```

---

## Local Development (without Docker)

### Prerequisites
- Python 3.12+
- Node.js 20+
- PostgreSQL 16 with `pgvector` and `citext` extensions

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp ../.env.example ../.env  # then edit DB host to 'localhost'
alembic upgrade head
python -m seeds.seed --if-empty
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Frontend | Next.js (App Router), React, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.12, async SQLAlchemy, Pydantic v2 |
| Database | PostgreSQL 16 + `pgvector` |
| Storage | Local FS (S3-ready abstraction) |
| Auth | Email/password, Argon2id, JWT |
| Document Processing | `pypdf`, `python-docx` |
| LLM | Provider abstraction over OpenAI, Anthropic, AWS Bedrock, Azure OpenAI, local stub |
| Deployment | Docker Compose (MVP); production path documented |

---

## What's Implemented in the MVP Foundation

✅ Architecture artifacts (7 docs)
✅ FastAPI app, async SQLAlchemy, Alembic, structured logging, error envelope
✅ All ORM models from the database-schema doc
✅ Auth: signup, login, refresh, logout, `/users/me`
✅ Workspaces + TeamMember + Company Profile + Capabilities
✅ Local BlobStore (S3 interface stubbed)
✅ LLM provider abstraction (OpenAI, Anthropic, Bedrock, Azure OpenAI, local_stub)
✅ Document upload + extraction (PDF / DOCX / TXT) + chunking + embeddings
✅ RAG retrieval engine with citations
✅ Module registry + `BaseIntelligenceModule`
✅ **Capture: Opportunity Summary** module wired end-to-end as the reference pattern
✅ SAM.gov market intelligence client + search + import + link-to-opportunity
✅ CSV exports (Compliance, Risks) — endpoints live, populated once those modules run
✅ AuditLog
✅ Frontend design system (tokens, primitives, briefing layout, citation chips)
✅ Platform shell with module-aware left nav and stubbed module groups
✅ Pages: Login, Signup, Dashboard, Workspaces, Opportunity list/detail, Documents, Module workbenches, Market Intelligence, Assistant
✅ Seed script with example opportunity + example documents
✅ Unit tests for auth, workspace scoping, LLM router, RAG

📋 Remaining Capture modules (Compliance Matrix, Evaluation Criteria, Requirement Breakdown, Win Themes, Capability Gaps, Staffing Assumptions, Proposal Outline, Risk Register, Market Intel Summary) — each follows the same ~50-line pattern as Opportunity Summary; see roadmap.

❌ Out of MVP scope by design: SSO, MFA, email flows, real-time collaboration, FedRAMP control implementation.

See the [Implementation Roadmap](docs/architecture/07-implementation-roadmap.md) for detail.

---

## Adding a New Intelligence Module

The platform is module-pluggable. To add (e.g.) `capture.compliance_matrix`:

1. Create `backend/app/llm/prompts/capture/compliance_matrix.v1.yaml`.
2. Create `backend/app/intelligence/modules/capture/compliance_matrix.py` extending `BaseIntelligenceModule`.
3. Register it in `backend/app/intelligence/registry.py`.
4. The frontend's `/capture/opportunities/[id]/compliance/page.tsx` already exists with a "Generate" CTA bound to `/modules/{module_id}/run` — no changes needed beyond the page's rendering layer.

To add a whole new module group (e.g. Operations Intelligence), see the [Implementation Roadmap, Milestone 6](docs/architecture/07-implementation-roadmap.md#milestone-6--second-module-group).

---

## License

Proprietary. © MissionIQ. All rights reserved.
