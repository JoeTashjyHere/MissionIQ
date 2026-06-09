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

## The MissionIQ Difference — Insight, Not Extraction

MissionIQ explicitly does **not** generate generic AI deliverables. Most
"AI for capture" tools paraphrase the RFP back at you. MissionIQ does
something different: before producing any consultant-grade output, it
synthesizes a portrait of the customer.

That portrait is the **Customer DNA Profile**. It is the platform's
central synthesis step and the input every downstream module reads.

```
Opportunity Documents ┐
Agency Mission         │
Agency Strategic Plans │
Operating Environment  │      ┌──────────────────────────┐
Evaluation Criteria    ├─►  │   Customer DNA Profile   │  ──► Compliance Matrix
Contract Context       │      │  • Mission                │  ──► Evaluation Criteria
Market Intelligence    │      │  • Strategic Goals        │  ──► Risk Register
Customer Profile       ┘      │  • Core Values            │  ──► (every future module)
                              │  • Success Metrics        │
                              │  • Operational Challenges │
                              │  • Technology Priorities  │
                              │  • Risk Priorities        │
                              │  • Stakeholder Concerns   │
                              └──────────────────────────┘
```

**Architectural guarantees:**

- Any module with `requires_customer_dna = True` **refuses to call the
  LLM** until a Customer DNA Profile exists. It returns
  `status = "insufficient_context"` with a CTA that links directly to the
  Customer DNA tab. There is no "generic" mode.
- Every downstream prompt renders the DNA Profile into the LLM context
  and instructs the model to tie its analytical claims to specific DNA
  attributes by name (e.g. *"Aligns with Strategic Goal #2:
  health-data interoperability"*).
- Structured writeback persists every consultant-grade row to its
  relational table (`compliance_requirement.why_requirement_exists`,
  `evaluation_criterion.evaluation_intelligence`, `risk.lane`,
  `risk.mission_impact`, …) so CSV exports and joined queries reflect
  the latest insight-grade analysis, not just raw JSON.

This is what makes MissionIQ outputs read like a senior capture manager
or management consultant produced them, rather than an AI summarizer.

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

## Golden Path Demo — Capture Intelligence

The end-to-end demo runs offline against the `local_stub` LLM. With a real
provider configured the same path produces substantive output.

1. **Sign in** at http://localhost:3000 with the demo credentials above. You
   land in the **Demo Workspace** with one example opportunity already
   created.
2. **Open the example opportunity** ("DHA Mission Operations Support
   Services") from the Capture Intelligence → Opportunities list. The
   **Briefing** tab shows the opportunity metadata, KPI summary, and tabs
   for every Capture module.
3. **Documents tab** — the seeded `example_rfp.txt` has already moved through
   `uploaded → parsing → chunking → embedding → ready`. Upload one of your
   own (PDF, DOCX, or TXT). The row shows:
   - The current processing stage as a friendly label
   - A live progress bar that advances 5 → 25 → 50 → 75 → 100
   - Page and chunk counts once available
   - A red error pill with the exact error message if processing fails
   Each transition is written to the **audit log** with stage, model, page,
   and chunk metadata.
4. **Customer DNA tab** — click **Generate Customer DNA Profile**. This is
   the platform's central synthesis step. MissionIQ produces:
   - **Mission** — what this customer uniquely exists to accomplish
   - **Strategic Goals** — the multi-year goals they are pursuing
   - **Core Values** — how they decide
   - **Success Metrics** — what they actually measure
   - **Operational Challenges** — frictions / unsolved problems
   - **Technology Priorities** — modernization initiatives
   - **Risk Priorities** — risks they are actively trying to reduce
   - **Stakeholder Concerns** — what named roles (CO, PM, Mission Owner,
     CIO, OIG) care about
   The DNA Profile is also surfaced as a card on the **Briefing** tab. If
   you skip this step, the next three modules will refuse to run.
5. **Opportunity Summary tab** — click **Generate Opportunity Summary**. The
   output renders four canonical sections (Executive Summary, Key Findings,
   Supporting Evidence, Recommended Actions). Every citation is clickable
   and hover-previews the document/page/snippet.
6. **Compliance Matrix tab** — click **Generate Compliance Matrix**. Every
   row carries the consultant-grade columns:
   - **Why Requirement Exists** — the underlying need or regulatory driver
   - **Mission Alignment** — the DNA Strategic Goal it ladders into
   - **Customer Priority** — critical / high / medium / low, derived from
     Section M weighting + DNA stakeholder concerns
   Rows are persisted to `compliance_requirement` so CSV export reflects
   the same insight payload.
7. **Evaluation Criteria tab** — click **Generate**. The output has two
   parts: a structured Section M decomposition (factor, subfactor,
   importance, required response elements) *and* the
   **Evaluation Intelligence** payload (Likely Decision Drivers, Potential
   Discriminators, Potential Weaknesses, Strategic Recommendations), each
   tied to specific DNA attributes by name.
8. **Risk Register tab** — click **Generate**. Risks are categorized
   into the four canonical capture lanes:
   - **Capture Risks** — threats to winning the bid
   - **Proposal Risks** — threats to producing a compliant proposal on time
   - **Delivery Risks** — threats to executing the contract after award
   - **Customer Risks** — threats to the customer's mission or reputation
   Every risk includes Mission Impact, Probability, Severity, Mitigation,
   and Supporting Evidence (E#/M# back to source).
9. **Intelligence Assistant tab** — start a thread. Try one of the suggested
   questions. Each answer carries a **Grounded** / **Insufficient context**
   status pill, lists source citations as `[1] [2] …` chips, and shows
   which model produced it. If you ask before any document is `ready`,
   the Assistant refuses *before* calling the LLM. The refusal is
   audit-logged as `chat.message.refused`.
10. **Audit trail** — every user-visible action above produces an
    `audit_log` row (`document.uploaded`,
    `document.processing.parsing/chunking/embedding/ready/failed`,
    `ai.module.run`, `chat.message.received`, `chat.message.sent`,
    `chat.message.refused`). Query it directly:

    ```sql
    SELECT created_at, action, target_type, meta
    FROM audit_log
    ORDER BY created_at DESC
    LIMIT 25;
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
✅ Document upload + extraction (PDF / DOCX / TXT) + chunking + embeddings, with live per-stage progress (`uploaded → parsing → chunking → embedding → ready / failed`) and audit log entries on every transition
✅ RAG retrieval engine with source-cited citations
✅ Module registry + `BaseIntelligenceModule` with `requires_customer_dna` prerequisite (downstream modules refuse to call the LLM without a DNA Profile)
✅ **Capture: Customer DNA Profile** module — the central synthesis step (Mission · Strategic Goals · Core Values · Success Metrics · Operational Challenges · Technology Priorities · Risk Priorities · Stakeholder Concerns)
✅ **Capture: Opportunity Summary** module (Executive Summary · Key Findings · Supporting Evidence · Recommended Actions)
✅ **Capture: Compliance Matrix** module — DNA-aware columns: Why Requirement Exists · Mission Alignment · Customer Priority, with structured writeback to `compliance_requirement`
✅ **Capture: Evaluation Criteria** module — Section M decomposition plus Evaluation Intelligence (Likely Decision Drivers · Potential Discriminators · Potential Weaknesses · Strategic Recommendations), persisted to `evaluation_criterion`
✅ **Capture: Risk Register** module — four-lane taxonomy (Capture · Proposal · Delivery · Customer) with Mission Impact · Probability · Severity · Mitigation · Supporting Evidence per risk, persisted to `risk`
✅ **Intelligence Assistant** with hard grounding contract: refuses to call the LLM when no documents are indexed or retrieval returns no hits; every answer carries citations and a status pill
✅ SAM.gov market intelligence client + search + import + link-to-opportunity
✅ CSV exports (Compliance, Risks) — populated by the structured writeback path
✅ AuditLog
✅ Frontend design system (tokens, primitives, briefing layout, citation chips)
✅ Platform shell with module-aware left nav and stubbed module groups
✅ Pages: Login, Signup, Dashboard, Workspaces, Opportunity list/detail, Documents, Module workbenches, Market Intelligence, Assistant
✅ Seed script with example opportunity + example documents
✅ Unit tests for auth, workspace scoping, LLM router, RAG, document status state machine, Opportunity Summary contract, Customer DNA contract, and the DNA-prerequisite enforcement for downstream modules

📋 Remaining Capture modules (Requirement Breakdown, Win Themes, Capability Gaps, Staffing Assumptions, Proposal Outline, Market Intel Summary) — each follows the same ~80-line pattern as the DNA-aware modules already shipped.

❌ Out of MVP scope by design: SSO, MFA, email flows, real-time collaboration, FedRAMP control implementation.

See the [Implementation Roadmap](docs/architecture/07-implementation-roadmap.md) for detail.

---

## Adding a New Intelligence Module

The platform is module-pluggable. To add (e.g.) `capture.win_themes`:

1. Create `backend/app/llm/prompts/capture/win_themes.v1.yaml`.
   - Set up an `EVIDENCE FROM UPLOADED DOCUMENTS` block.
   - **If your module consumes the Customer DNA Profile** (which it almost
     certainly should), add a `CUSTOMER DNA PROFILE` block that renders
     `{{ customer_dna.mission }}`, `{{ customer_dna.strategic_goals }}`,
     etc., and instruct the LLM to tie each analytical claim to a named
     DNA attribute.
2. Create `backend/app/intelligence/modules/capture/win_themes.py` extending
   `BaseIntelligenceModule`. Set `requires_customer_dna = True` if the
   module reads the DNA — the orchestrator will load the latest profile
   and refuse to call the LLM if one does not exist yet, returning a
   friendly `_missing_dependency: "customer_dna"` payload that the UI
   surfaces as a deep-link to the DNA tab.
3. Register it in `backend/app/intelligence/registry.py`.
4. Define a Pydantic `*Output` schema in `backend/app/schemas/intelligence.py`
   and bind it to the module via `output_model`. The orchestrator
   validates every LLM payload against this schema.
5. The frontend page at `/capture/opportunities/[id]/win-themes/page.tsx`
   already exists with a `ModuleWorkbench` wrapper — just supply an
   `outputRenderer` that consumes the AI output and citations.
6. *(Optional)* If your module maps to a first-class relational table
   (like Compliance / Evaluation / Risk), add a structured writeback
   helper in `backend/app/services/intelligence_service.py` so CSV
   exports and joined queries pick it up.

To add a whole new module group (e.g. Operations Intelligence), see the [Implementation Roadmap, Milestone 6](docs/architecture/07-implementation-roadmap.md#milestone-6--second-module-group).

---

## License

Proprietary. © MissionIQ. All rights reserved.
