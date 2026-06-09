# MissionIQ — System Architecture

> **MissionIQ** is the Operational Intelligence Platform.
> Capture Intelligence is the first module shipped in the MVP.
> All architectural decisions in this document optimize for a multi-module future.

---

## 1. Architectural Principles

| # | Principle | Implication |
|---|-----------|-------------|
| 1 | **Platform-first, module-second** | The platform owns identity, workspaces, documents, retrieval, audit, LLM. Modules own only their domain logic and outputs. |
| 2 | **Workspace is the tenancy boundary** | Every queryable row carries `workspace_id`. Every API call is scoped. Future SSO/SCIM operates at workspace granularity. |
| 3 | **Source-cited or it didn't happen** | No AI output is rendered without `(document, page, chunk)` or `(market_record, source_url)` provenance. |
| 4 | **Model-agnostic AI** | Application code calls an `LLMClient` interface, never a vendor SDK directly. |
| 5 | **Storage-agnostic blobs** | Application code calls a `BlobStore` interface; local FS today, S3 / GovCloud S3 later, with zero call-site changes. |
| 6 | **Public ≠ customer data** | Public market intel (SAM.gov) lives in shared tables. Customer uploads and licensed feeds (GovWin) live in workspace-scoped tables, never cross-pollinated. |
| 7 | **Auditability is a feature, not a log** | `audit_log` and `ai_output` records are first-class entities, surfaced in the UI. |
| 8 | **FedRAMP-ready, not FedRAMP-implemented** | We do not deploy to GovCloud today, but no design decision precludes it (no consumer SaaS dependencies, no telemetry leak, no foundation-model training on customer data). |

---

## 2. High-Level Component Diagram

```
                       ┌──────────────────────────────────────────────────┐
                       │                  Browser (Next.js)                │
                       │  ┌──────────────┐  ┌────────────────────────────┐ │
                       │  │ Platform Shell│  │  Module Workbenches        │ │
                       │  │  (left nav,   │  │  • Capture Intelligence    │ │
                       │  │   top bar,    │  │  • (Operations) [future]   │ │
                       │  │   workspace)  │  │  • (Process)    [future]   │ │
                       │  └──────────────┘  └────────────────────────────┘ │
                       └─────────────────────────┬────────────────────────┘
                                                 │  HTTPS / JSON (Bearer JWT)
                                                 ▼
                       ┌──────────────────────────────────────────────────┐
                       │              FastAPI Gateway (api/v1)             │
                       │  Auth · Workspaces · Opportunities · Documents    │
                       │  Market Intel · Modules · Chat · Exports · Audit  │
                       └──────┬─────────────┬──────────────┬───────────────┘
                              │             │              │
              ┌───────────────┘             │              └────────────────┐
              ▼                             ▼                               ▼
     ┌────────────────┐         ┌────────────────────┐           ┌────────────────────┐
     │  Service Layer │         │  Intelligence Core │           │   Integrations     │
     │  • Auth        │         │  • Module Registry │           │  • SAM.gov client  │
     │  • Workspace   │◀───────▶│  • RAG Engine      │◀─────────▶│  • GovWin adapter  │
     │  • Document    │         │  • LLM Router      │           │    (workspace-bound)│
     │  • Audit       │         │  • Prompt Library  │           │  • CRM adapters    │
     └───────┬────────┘         └─────────┬──────────┘           └─────────┬──────────┘
             │                            │                                │
             ▼                            ▼                                ▼
     ┌────────────────┐         ┌────────────────────┐           ┌────────────────────┐
     │  PostgreSQL    │         │   pgvector index   │           │   BlobStore        │
     │  (relational)  │         │   (embeddings)     │           │   (local → S3)     │
     └────────────────┘         └────────────────────┘           └────────────────────┘
```

---

## 3. Logical Layers

### 3.1 Presentation Layer — Next.js (App Router)
- **Platform Shell**: persistent left nav, workspace switcher, module switcher, executive top bar.
- **Module Workbenches**: each intelligence module is a route segment (`/capture`, `/operations` [stub], …) that consumes shared design-system primitives.
- **Design System**: tokens (color, typography, spacing), primitives (Button, Card, KPI, DataTable, Citation, BriefingSection), patterns (Executive Page, Compliance Table, Risk Register).
- **AI surface area is bounded**: chat is a side panel, never the home page. Every page leads with Executive Summary → Key Findings → Supporting Evidence → Recommended Actions.

### 3.2 API Layer — FastAPI
- Versioned under `/api/v1`.
- All routes (except `/auth/*` and `/health`) require `Authorization: Bearer <jwt>` and resolve a `workspace_id` from the path or selected workspace.
- A `WorkspaceScope` dependency enforces row-level access; no service function trusts a caller-supplied `workspace_id`.

### 3.3 Service Layer — Python
- Pure business logic, no HTTP concerns.
- Services are constructed per-request with injected `db`, `blob_store`, `llm_router`, `audit`.
- Every write path emits an `AuditLog` row.

### 3.4 Intelligence Core
- **Module Registry**: each intelligence module (`OpportunitySummary`, `ComplianceMatrix`, …) registers itself with metadata (id, label, module group, required inputs, output schema, prompt template id).
- **RAG Engine**: `retrieve(query, scope) → List[Evidence]` where `Evidence = {chunk_id, document_id, page, section, snippet, score}`. Scope is always `(workspace_id, opportunity_id?, include_market_intel?)`.
- **LLM Router**: selects a provider/model based on (a) module preference, (b) workspace policy, (c) availability. Returns a normalized `LLMResponse` with token accounting.
- **Prompt Library**: prompts are versioned files, never inline strings. Each prompt has an `id`, `version`, `input_schema`, `output_schema`.

### 3.5 Persistence Layer
- **PostgreSQL** for relational data + `pgvector` for embeddings (single database, separate schemas optional).
- **BlobStore** for original files (PDF/DOCX/TXT) — local FS for MVP, S3-compatible for production.

### 3.6 Integration Layer
- **SAM.gov** (public API, key-based).
- **GovWin** (customer-authorized adapter; data is workspace-bound, never trained on, never redistributed).
- **CRM / SharePoint / Salesforce** (future adapters share the same `MarketIntelSource` contract).

---

## 4. Request Lifecycle (Example: "Generate Opportunity Summary")

```
1. User clicks "Generate" on Opportunity Summary page
   POST /api/v1/opportunities/{opp_id}/modules/opportunity-summary/run

2. FastAPI route validates JWT → loads User → resolves workspace_id from opp_id
   (404 if opp doesn't belong to user's workspace)

3. CaptureService.run_module("opportunity-summary", opp_id):
     a. ModuleRegistry.get("opportunity-summary") → module spec
     b. RAGEngine.retrieve(
          query=module.retrieval_query,
          scope=(workspace_id, opp_id, include_market_intel=True)
        ) → List[Evidence]
     c. PromptLibrary.render("opportunity_summary.v1", evidence=...)
     d. LLMRouter.generate(prompt, model=workspace.policy.default_model)
     e. Validate response against module.output_schema (Pydantic)
     f. Persist AIOutput row with: module_id, opp_id, model, tokens,
        prompt_version, evidence_ids[], output_json
     g. AuditLog.write("ai.generate", actor=user, target=opp_id, meta={...})

4. Response: { output_json, citations: [...], generated_at, model, tokens }

5. Frontend renders Executive Summary / Key Findings / Evidence / Actions,
   each bullet linked to its citation hover-card.
```

---

## 5. Module Extensibility Pattern

Adding a new module (e.g., **Operations Intelligence → SLA Tracker**) requires:

1. Add a row to `module_registry` (db-seeded constant).
2. Drop a prompt file in `backend/app/prompts/operations/sla_tracker.v1.yaml`.
3. Implement `OperationsModule(BaseIntelligenceModule)` with `retrieve()` and `postprocess()` hooks.
4. Add a Next.js route segment `frontend/app/(app)/operations/sla-tracker/page.tsx`.
5. Add a nav entry under the `operations` module group.

**No changes required** to: auth, workspaces, documents, RAG, LLM router, audit, design system primitives.

---

## 6. Multi-Tenancy Model

- **Single DB, row-level isolation by `workspace_id`** for MVP.
- All workspace-scoped tables have a `workspace_id` FK + composite index `(workspace_id, ...)` on every common query.
- Postgres Row-Level Security (RLS) policies are **defined but optional in dev**, **mandatory in production** — see Security Architecture doc.
- Path to dedicated-tenant deployment: same schema, separate database per tenant, routed by workspace ID at the connection-pool level. No app changes required.

---

## 7. Data Classification

| Class | Examples | Storage | Cross-Workspace? |
|-------|----------|---------|------------------|
| **Public** | SAM.gov notices, NAICS taxonomy | `market_intel_record` (no workspace_id) | Yes (shared) |
| **Customer Uploaded** | RFPs, SOWs, capture notes | `document`, `document_chunk` | **No** |
| **Customer Licensed** | GovWin pulls, CRM exports | `market_intel_record` w/ workspace_id | **No** |
| **Derived AI Output** | Compliance matrices, summaries | `ai_output` | **No** |
| **Telemetry** | Audit logs, user actions | `audit_log` | **No** |

The same `MarketIntelRecord` table holds both public and customer-licensed records; **the presence of `workspace_id` is the classification signal**. Queries always filter accordingly.

---

## 8. AI Governance

- **No foundation-model training on customer data**: enforced by provider configuration (e.g., OpenAI `store=false`, Anthropic no-training default, Bedrock customer-managed) and contractually upstream.
- **Retrieval-augmented only**: modules never call the LLM without grounding evidence (or explicitly mark output as `ungrounded=true`, which the UI renders with a warning).
- **Citations are mandatory**: the output schema for every module includes a `citations: List[CitationRef]` field; rendering layer refuses to display claims without them.
- **Insufficient-context paths**: when `len(evidence) < threshold`, the LLM is instructed to return `{ "status": "insufficient_context", "missing": [...] }` and the UI surfaces a "Data gaps" panel instead of fabricating an answer.

---

## 9. Deployment Topology (MVP)

```
docker-compose.yml
├── postgres        (postgres:16 + pgvector extension)
├── backend         (FastAPI, uvicorn, python:3.12)
├── frontend        (Next.js, node:20)
└── (optional) mailhog for dev email
```

Production path (out of MVP scope, but compatible):
- Postgres → managed (RDS / Aurora / GovCloud RDS)
- Backend → containers behind ALB
- Frontend → Vercel or self-hosted Next.js node
- Blobs → S3 / S3 GovCloud
- Secrets → AWS Secrets Manager / Parameter Store

---

## 10. Non-Functional Requirements

| Concern | MVP Target | Future |
|---------|-----------|--------|
| Auth | Email/password + JWT (30-min access, 14-day refresh) | SSO (OIDC/SAML), SCIM provisioning, MFA |
| Authz | Workspace membership + role (owner/admin/member/viewer) | Fine-grained per-opportunity ACLs |
| Audit | Append-only `audit_log` table | Streaming to SIEM (Splunk/Datadog) |
| Logging | Structured JSON to stdout | Centralized (CloudWatch / Datadog) |
| Observability | `/health`, request-id middleware | Distributed tracing (OTel) |
| Rate limiting | Per-IP on `/auth/*` (in-memory MVP) | Distributed (Redis) |
| File size | 50 MB / upload | 500 MB + chunked |
| Concurrency | Synchronous module runs, background task for embeddings | Job queue (Celery/RQ) |
| Latency | Module runs < 30s p95 | Streaming responses |

---

## 11. Out of Scope for MVP (Documented for Roadmap)

- SSO / SAML / SCIM
- Real-time collaboration on opportunities
- Workflow / approvals
- Email notifications
- Mobile app
- Pricing module
- Production observability stack
- FedRAMP control implementation (only **alignment**)
