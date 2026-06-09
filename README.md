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

### Both sides of the deal — Customer DNA × Company DNA

Customer DNA captures **who the customer is**. The seller-side layer captures
**who *we* are and whether we can credibly win and deliver**.

```
Company Profile ┐
 • Core capabilities          ┌─────────────────────┐
 • Past performance           │   Company DNA       │
 • Contract vehicles      ──► │  (seller portrait)  │ ─┐
 • Certifications / partners   └─────────────────────┘  │
 • Differentiators / footprint                          │   ┌──────────────────┐
 • Security / delivery / pricing                         ├─► │ Capability Match │
                                                         │   │  • Strong/weak   │
Customer DNA ────────────────────────────────────────── ┤   │  • Gaps / proof  │
Opportunity requirements (RAG) ───────────────────────── ┤   │  • Teaming       │
Evaluation criteria (prior module output) ────────────── ┤   │  • Discriminators│
Market intelligence (RAG) ────────────────────────────── ┘   │  • Win themes    │
                                                              │  • Capture Qs    │
                                                              │  • Gap risks     │
                                                              └──────────────────┘
```

**Seller-side guarantees:**

- **Company Profile is the seller source of truth** (workspace-level, edited on
  the Company Profile page). Company DNA synthesizes it; Capability Match
  consumes it.
- **Capability Match never overclaims.** When the Company Profile is empty or
  thin, it sets `seller_data_complete = false`, caps `fit_score` at
  `moderate`, prefixes fit claims with `[Assumption — Company Profile
  incomplete]`, and links the user to complete the profile. A capture lead is
  never misled into thinking a fit verdict was grounded in real company data.
- **Company Profile is optional for downstream modules.** Compliance,
  Evaluation, and Risk set `consumes_company_profile = True`: they still run on
  Customer DNA alone, but when seller data is present they sharpen
  discriminators / seller-gap risks, and when it is absent they label
  seller-side notes as assumptions.

### The apex — Win Strategy Engine (flagship deliverable)

Everything above feeds the **Win Strategy** module (`capture.win_strategy`) —
the culminating, gate-review-grade deliverable. It does **not** summarize
documents; it synthesizes them into a senior-capture-executive assessment.

```
Customer DNA ─┐
Company DNA   │
Opp Documents │     ┌──────────────────────────────┐
Eval Criteria ├──►  │        Win Strategy          │
Capability    │     │  1. Executive Pursuit Rec.   │
  Match       │     │  2. Strengths                │
Market Intel  │     │  3. Weaknesses               │
Risk Register ┘     │  4. Key Discriminators       │
                    │  5. Black Hat Assessment     │
                    │  6. Likely Evaluator Concerns│
                    │  7. Win Themes               │
                    │  8. Competitive Assessment   │
                    │  9. Critical Capture Actions │
                    │ 10. Win Confidence (0–100)   │
                    └──────────────────────────────┘
```

**Flagship guarantees:**

- **Synthesis, not summary.** The prompt deletes any line that merely restates
  the RFP. Every line must advance a strategic position.
- **Epistemic honesty.** Every point declares a `basis` —
  `evidence` (backed by a cited input), `inference` (defensible judgment), or
  `assumption` (a belief to validate). Evidence points must carry `sources`
  (`Customer DNA: mission`, `Company DNA: differentiators`, `E2`, `M1`, …). The
  UI renders these as colored chips so a gate review sees exactly what is proven
  vs inferred vs assumed.
- **Partial-input integrity.** Win Strategy requires only Customer DNA, but it
  reads Company DNA, Capability Match, Evaluation Criteria, and the Risk
  Register when present. Missing inputs are recorded in `inputs_missing`, the
  affected conclusions drop to inference/assumption, and the win-confidence
  score is dampened — it never fakes evidence it does not have.

---

### Institutional memory — the Knowledge Graph layer

Reports above are *opportunity-specific*. The **Memory & Knowledge Graph** layer
turns them into *institutional* intelligence so MissionIQ gets smarter with
every opportunity processed. It is a reusable layer, **not another report**.

```
Every module run ──► extract structured facts ──► Knowledge Graph
                                                   (workspace-scoped)
        Entities: Agency · Program · Opportunity · Contract · Competitor
                  Technology · Capability · Risk · Win Theme · Discriminator
                  Contract Vehicle · Past Performance
        Edges:    provenance-stamped (opportunity_id + module_id), idempotent

Knowledge Graph ──► Memory service ──►  1. Pursuit Memory
                                        2. Opportunity Similarity Engine
                                        3. Historical Insight Repository
                                        4. Agency Intelligence Repository
                                            │
                                            └──► powers future reports
                                                 (Win Strategy consumes it)
```

**How it works:**

- **Contribution.** After any module succeeds, `app/graph` extracts structured
  facts and `graph_service.ingest_module_output` upserts deduplicated entities
  and provenance-stamped edges. A module re-run replaces *only its own* edges, so
  the graph never double-counts. Risk Register → risks; Capability Match →
  discriminators / win themes / capability gaps; Win Strategy → win themes /
  discriminators / competitors; Customer DNA enriches the Agency node; and the
  opportunity record itself contributes agency / vehicle / incumbent.
- **Recall.** When a new opportunity is analyzed, the **Opportunity Similarity
  Engine** ranks prior pursuits by agency, sub-agency, NAICS, contract vehicle,
  and shared technology/capability/competitor signals. **Pursuit Memory** then
  surfaces prior risks, prior discriminators, and prior win themes drawn from
  similar and same-agency pursuits.
- **Epistemic honesty.** Every recalled item is tagged
  `historical` (from prior pursuits), `current` (on this opportunity), or
  `inference` (MissionIQ's aggregated judgment) — the platform-wide distinction
  between **Historical Evidence**, **Current Opportunity Evidence**, and
  **Inference**.
- **Powers future reports.** Modules opt in with `consumes_memory = True`. The
  flagship **Win Strategy** consumes Pursuit Memory and folds recurring prior
  risks / discriminators / win themes into its assessment, citing
  `Pursuit Memory` as Historical Evidence — distinct from current-document
  evidence (`E<n>`).

Surfaced read-only on the **Memory** tab (per opportunity) and the
`GET /opportunities/{id}/memory` + `GET /workspaces/{id}/insights` endpoints.

### Decisions — Executive Briefings & Gate Reviews

Everything above produces *intelligence*. The **Briefings** layer turns that
intelligence into *leadership decisions* — boardroom-ready packages that answer
"What should we do?" and "How do we communicate it to leadership?". Each briefing
synthesizes every upstream output (Customer DNA, Company DNA, Capability Match,
Evaluation & Risk Intelligence, Win Strategy, market intelligence, and Pursuit
Memory) and consumes `requires_customer_dna`, `consumes_company_profile`, and
`consumes_memory`.

```
All intelligence ──►  Executive Brief   (capture.executive_brief)
                      Gate Review       (capture.gate_review)
                      Bid / No-Bid      (capture.bid_decision)
```

- **Executive Brief** — a one-screen brief: opportunity snapshot, customer
  intelligence, company position, win strategy, risks (capture/proposal/delivery
  heat map), and an executive recommendation (Pursue Aggressively · Pursue with
  Conditions · Monitor · No-Bid) with confidence, rationale, and required
  conditions.
- **Gate Review** — a formal gate-review package: 0–100 scores for Opportunity
  Attractiveness, Competitive Position, Capability Alignment, and Risk; a
  Probability of Win; top reasons to pursue / not pursue; the decision
  recommendation; required executive actions; open questions; and escalations.
- **Bid / No-Bid Decision** — a focused call (Bid · Conditional Bid · No-Bid)
  scored across the six decision factors (Strategic Alignment, Revenue Potential,
  Relationship Position, Competitive Position, Delivery Readiness, Risk Profile),
  each with score, rationale, evidence, and confidence — plus decision drivers
  and required next steps.

**Epistemic honesty everywhere.** Every analytic statement is tagged
**Evidence** (what MissionIQ knows), **Inference** (what it believes), or
**Assumption** (what needs validating), and recalled institutional knowledge is
surfaced as **Historical Evidence**. The briefing pages are built from a modular,
slide-mappable design system (`components/briefings`) — KPI banner, confidence
gauge, recommendation banner, score bars, risk heat map, strength/weakness
matrix, action tracker, and a historical-evidence panel — so they can later
export 1:1 to PowerPoint / PDF / Word.

### Platform navigation

The left navigation is organized around platform capabilities (Win · Deliver ·
Improve), not individual reports: **Capture Intelligence**, **Briefings**,
**Memory**, **Market Intelligence**, **Platform**, and disabled **Future
Modules**. Capture / Briefings / Memory items are opportunity-scoped, so they
deep-link into the currently open opportunity and otherwise route to the
Opportunities list. Routes are unchanged — only the information architecture was
reorganized.

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
9. **Company Profile + Company DNA** — open **Settings → Company Profile** and
   review the seeded seller-side data (capabilities, past performance,
   contract vehicles, certifications, technology partners, differentiators,
   case studies, key personnel, footprint, security posture, delivery model,
   pricing posture). Back on the opportunity, open the **Company DNA** tab and
   click **Generate Company DNA Profile** — the seller-side mirror of Customer
   DNA, synthesized from the Company Profile (no opportunity documents
   required). Clear the profile and regenerate to see it report
   `profile_completeness = "empty"` with a CTA to complete the profile.
10. **Capability Match tab** — click **Generate Capability Match**. This is the
    senior-capture-lead fit assessment. It compares Customer DNA, opportunity
    requirements, evaluation criteria, market intelligence, and the Company
    Profile, and returns the candid **"can we credibly win and deliver?"**
    verdict plus strong/weak fit areas, missing capabilities, required proof
    points, recommended teaming partners, suggested discriminators, reusable
    win themes, capture questions, and proposal risks tied to company gaps.
    The verdict also surfaces as a card on the **Briefing** tab.     With an empty
    Company Profile it still runs on Customer DNA, but flags
    `seller_data_complete = false` and labels every fit claim as an assumption.
11. **Win Strategy tab (flagship)** — click **Generate Win Strategy**. This is
    the gate-review deliverable. MissionIQ synthesizes Customer DNA, Company
    DNA, opportunity documents, evaluation criteria, Capability Match, market
    intelligence, and the Risk Register into an executive briefing:
    - **Executive Pursuit Recommendation** (pursue / pursue-with-conditions /
      no-bid) and a **Win Confidence** gauge (0–100)
    - **Strengths · Weaknesses · Key Discriminators**, each tagged
      **Evidence / Inference / Assumption** with source chips
    - **Black Hat Assessment** (how a competitor attacks us + our counter)
    - **Likely Evaluator Concerns · Win Themes · Competitive Assessment**
    - **Critical Capture Actions** (immediate / near-term / pre-RFP)
    Generate it with only Customer DNA to see it run on partial inputs (lower
    confidence, `inputs_missing` banner), then generate the upstream modules
    and regenerate to watch confidence rise and assumptions become evidence.
    The recommendation also surfaces as the top card on the **Briefing** tab.
12. **Memory tab (institutional intelligence)** — open the **Memory** tab. Every
    module you ran above contributed structured facts to the workspace
    Knowledge Graph, so this page shows MissionIQ's recall for the pursuit:
    **Similar Prior Pursuits** (ranked by agency / vehicle / NAICS / shared
    signals), **Prior Risks · Prior Discriminators · Prior Win Themes**, an
    **Agency Intelligence** panel, and what MissionIQ **infers**. Each item is
    tagged **Historical Evidence**, **Current Opportunity**, or **Inference**.
    Create and analyze a second opportunity for the same agency, then revisit
    this tab to watch similar pursuits and recurring intelligence appear — and
    re-run **Win Strategy**, which now cites **Pursuit Memory** as Historical
    Evidence. Workspace-wide reuse is also exposed at
    `GET /workspaces/{id}/insights`.
13. **Intelligence Assistant tab** — start a thread. Try one of the suggested
   questions. Each answer carries a **Grounded** / **Insufficient context**
   status pill, lists source citations as `[1] [2] …` chips, and shows
   which model produced it. If you ask before any document is `ready`,
    the Assistant refuses *before* calling the LLM. The refusal is
    audit-logged as `chat.message.refused`.
14. **Audit trail** — every user-visible action above produces an
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
✅ **Capture: Company DNA Profile** module — the seller-side mirror of Customer DNA (Core Capabilities · Past Performance · Contract Vehicles · Certifications · Technology Partners · Differentiators · Case Studies · Key Personnel · Footprint · Security Posture · Delivery Model · Pricing Posture), synthesized from the workspace Company Profile without requiring opportunity documents
✅ **Capture: Capability Match** module — senior-capture-lead fit assessment comparing Customer DNA × opportunity requirements × evaluation criteria × market intelligence × Company Profile, producing strong/weak fit, missing capabilities, required proof points, teaming recommendations, discriminators, win themes, capture questions, and company-gap proposal risks; refuses to overclaim when seller data is incomplete (`seller_data_complete = false`)
✅ **Seller-side Company Profile** expanded with contract vehicles, technology partners, case studies, key personnel, geographic footprint, security posture, delivery model, and pricing posture (editable on the Company Profile page); downstream modules optionally consume it (`consumes_company_profile`)
✅ **Capture: Win Strategy** module (flagship) — gate-review synthesis of Customer DNA, Company DNA, opportunity documents, evaluation criteria, Capability Match, market intelligence, and risks into Executive Pursuit Recommendation, Strengths, Weaknesses, Key Discriminators, Black Hat Assessment, Likely Evaluator Concerns, Win Themes, Competitive Assessment, Critical Capture Actions, and a 0–100 Win Confidence call. Every point is tagged evidence / inference / assumption with cited sources; partial inputs dampen confidence rather than fabricate evidence
✅ **Memory & Knowledge Graph** layer — a workspace-scoped institutional graph (Agency · Program · Opportunity · Contract · Competitor · Technology · Capability · Risk · Win Theme · Discriminator · Contract Vehicle · Past Performance) that every module contributes provenance-stamped facts to on success (idempotent ingestion). Powers four reusable capabilities — **Pursuit Memory**, the **Opportunity Similarity Engine**, the **Historical Insight Repository**, and the **Agency Intelligence Repository** — surfaced on the per-opportunity **Memory** tab and consumed by Win Strategy (`consumes_memory`), with every item tagged **Historical Evidence / Current Opportunity / Inference**
✅ **Briefings: Executive Brief / Gate Review / Bid · No-Bid Decision** modules — leadership decision packages that synthesize every upstream output (Customer DNA, Company DNA, Capability Match, Evaluation & Risk Intelligence, Win Strategy, market intelligence, Pursuit Memory) into a one-screen executive brief, a scored gate-review package, and a focused bid/no-bid call. Every statement is tagged Evidence / Inference / Assumption; recalled intelligence is labeled Historical Evidence; partial inputs dampen confidence. Built on a modular, slide-mappable briefing design system (`components/briefings`) ready for PowerPoint / PDF / Word export
✅ **Platform navigation** reorganized around capabilities (Win · Deliver · Improve): Capture Intelligence · Briefings · Memory · Market Intelligence · Platform · Future Modules, with opportunity-scoped sections that deep-link into the open pursuit (routes unchanged)
✅ **Intelligence Assistant** with hard grounding contract: refuses to call the LLM when no documents are indexed or retrieval returns no hits; every answer carries citations and a status pill
✅ SAM.gov market intelligence client + search + import + link-to-opportunity
✅ CSV exports (Compliance, Risks) — populated by the structured writeback path
✅ AuditLog
✅ Frontend design system (tokens, primitives, briefing layout, citation chips)
✅ Platform shell with module-aware left nav and stubbed module groups
✅ Pages: Login, Signup, Dashboard, Workspaces, Opportunity list/detail, Documents, Module workbenches, Market Intelligence, Assistant
✅ Seed script with example opportunity + example documents
✅ Unit tests for auth, workspace scoping, LLM router, RAG, document status state machine, Opportunity Summary contract, Customer DNA contract, the DNA-prerequisite enforcement for downstream modules, the Company DNA + Capability Match contracts, the seller-data anti-overclaim guarantee, the Win Strategy synthesis contract (basis tagging + partial-input confidence dampening + Pursuit Memory consumption), the Memory/Knowledge-Graph layer (fact extraction, entity normalization/dedup, similarity scoring, and Historical/Current/Inference basis classification), and the Executive Briefings & Gate Reviews contracts (registration/flags, decision-not-summary prompts, schema-valid stub output, Historical Evidence from memory, and partial-input confidence dampening)

📋 Remaining Capture modules (Requirement Breakdown, Win Themes, Staffing Assumptions, Proposal Outline, Market Intel Summary) — each follows the same ~80-line pattern as the modules already shipped.

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
   surfaces as a deep-link to the DNA tab. Set
   `consumes_company_profile = True` to receive the seller-side
   `company_profile` dict and a `seller_incomplete` flag in the prompt
   context (optional — the module still runs without a profile, but should
   label seller-side claims as assumptions when `seller_incomplete` is true).
   Override `extra_context()` if you need to inject prior module outputs
   (Capability Match does this to pull the latest Evaluation Criteria). Set
   `consumes_memory = True` to receive a compact **Pursuit Memory** view
   (`memory`) — prior risks / discriminators / win themes recalled from similar
   pursuits — which the prompt should cite as Historical Evidence (Win Strategy
   does this). To contribute facts back to the Knowledge Graph, add an
   extractor branch in `backend/app/graph/extract.py`; ingestion runs
   automatically on every successful module run.
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
