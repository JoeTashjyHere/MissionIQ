# MissionIQ — Implementation Roadmap

This roadmap describes the build order. The MVP foundation produced in this initial scaffolding completes through **Milestone 3** (one reference module wired end-to-end) and stubs Milestones 4–6 so they slot in without architectural change.

---

## Milestone 0 — Repository Foundation ✅ (this commit)

- Architecture documents (this folder)
- Repo root: README, `.env.example`, `.gitignore`, `docker-compose.yml`
- Folder structure per `02-folder-structure.md`

## Milestone 1 — Platform Foundation ✅

**Backend**
- FastAPI app factory with config, structured logging, error envelope, request-id middleware
- Async SQLAlchemy + Alembic, Postgres + pgvector + citext extensions
- All ORM models for every entity in `03-database-schema.md`
- Initial migration
- Argon2 password hashing + JWT issuance/verification
- Auth endpoints (signup/login/refresh/logout/me)
- Workspace + TeamMember CRUD with role-based authorization
- Company Profile + Capabilities CRUD
- AuditLog service
- Local BlobStore + storage interface (S3 stub)
- LLM provider interface + local stub provider + OpenAI provider + Anthropic provider
- PromptLibrary loader (YAML) + first prompt (`opportunity_summary.v1`)
- RAGEngine: cosine-similarity retrieval over `document_chunk.embedding`, scope-aware
- Document upload + sync extraction (PDF/DOCX/TXT) + chunking + embedding via EmbeddingClient (stub-capable)
- Module registry + `BaseIntelligenceModule`
- `capture.opportunity_summary` implemented end-to-end (retrieve → prompt → generate → validate → persist `AIOutput` → audit)
- SAM.gov client + market intel search endpoint + record save
- CSV exports for compliance + risk (endpoints; rows populated when those modules run)
- Unit tests for auth, workspace scoping, LLM router selection, RAG ranking, document ingestion

**Frontend**
- Next.js App Router + Tailwind + tokens.css + Inter/JetBrains fonts
- Design system primitives: Button, Card, Badge, StatusPill, Input, Select, Textarea, DataTable, KpiCard, Citation, BriefingSection, EmptyState, Skeleton, Toast, Drawer, Modal
- PlatformShell: LeftNav (module-aware, with stub groups), TopBar with Workspace switcher, Module Switcher
- Login / Signup pages with split-pane brand layout
- Dashboard (Executive Dashboard with KPI cards, recent opportunities, recent AI outputs)
- Workspace list / detail / settings / team / company profile / capabilities pages
- Opportunity list + new + detail (briefing layout)
- Document upload + list + status
- Module pages — Opportunity Summary fully wired; others as `EmptyState` with "Generate" CTA wired to the same `/modules/{id}/run` endpoint (works as soon as backend prompt is added)
- Market Intelligence search + records pages (SAM.gov)
- Intelligence Assistant (chat drawer scaffolded)
- Stubs for Operations / Process / Performance / Risk / Organizational / Market Intelligence module pages (clearly labeled, no fake content)

**Dev experience**
- `docker-compose up` brings up Postgres + backend + frontend
- Seed script creates demo workspace, user, example opportunity, ingests example RFP

## Milestone 2 — Complete Capture Modules

For each remaining module, the work is: add a YAML prompt, add a `BaseIntelligenceModule` subclass (~50 LOC), connect the existing frontend "Generate" CTA to the registered module id, and add a structured-view page when needed (Compliance, Risks, Evaluation).

- `capture.compliance_matrix` + structured `compliance_requirement` write-back + editable table + CSV
- `capture.evaluation_criteria` + structured `evaluation_criterion` write-back
- `capture.requirement_breakdown` (categorization only — no extra table)
- `capture.win_themes`
- `capture.capability_gaps` (cross-references `capability` table)
- `capture.staffing_assumptions`
- `capture.proposal_outline`
- `capture.risk_register` + structured `risk` write-back + editable table + CSV
- `capture.market_intel_summary`
- Intelligence Assistant: full chat retrieval over opportunity + market intel; insufficient-context handling

## Milestone 3 — Hardening & DX

- Background-task queue (FastAPI BackgroundTasks → Celery/RQ migration path)
- Per-workspace rate limiting on module runs
- Per-workspace storage quotas (display + enforcement)
- Better embedding pipeline (batching, retries, partial failures)
- Frontend: `⌘K` global search across opportunities + documents + market records
- Frontend: Evidence Drawer with full chunk highlighting

## Milestone 4 — Integrations

- GovWin adapter (customer-supplied credentials, encrypted at rest)
- SharePoint + Salesforce adapters (OAuth)
- Internal proposal repository import (file tree → batch document upload)

## Milestone 5 — Production Readiness

- RS256 JWT with KMS-backed key
- Postgres RLS enabled and tested
- S3 BlobStore + per-workspace KMS keys
- Email service (transactional: invite, password reset)
- SSO (OIDC) for at least one IdP (Okta or Azure AD)
- SCIM provisioning
- Structured request tracing (OTel)
- Centralized logging
- AV scan implementation (ClamAV)
- WAF + rate limit at edge

## Milestone 6 — Second Module Group

The first new module group (proposal: **Operations Intelligence — SLA Tracker**) demonstrates platform extensibility:

- Add `operations.*` group to module registry
- Add `OperationsIntelligenceModule` base class (reuses `BaseIntelligenceModule`)
- Add `OperationalDocument` doc types (CDRLs, monthly reports, contracts) to `document.doc_type` enum (Alembic migration)
- Add `/operations/*` Next.js route group
- Activate the LeftNav stub for Operations Intelligence
- No changes required to auth, workspaces, RAG, LLM router, design system

Estimated time-to-second-module after MVP: **~2 weeks** of focused work, validating the platform-first architecture.

## Milestone 7 — GovCloud / FedRAMP Path

- Deploy to AWS GovCloud (US)
- Wire KMS-backed JWT + per-workspace KMS keys
- Enable Postgres RLS in all environments
- ATO documentation: SSP, control narratives mapped to NIST 800-53 Moderate baseline
- Independent assessment
- Continuous monitoring stack

---

## Definition of Done (per milestone)

A milestone is "done" when:
1. All listed work is merged and passing tests.
2. README/architecture docs updated for any deviation.
3. `docker-compose up` from a clean clone reaches a healthy state in <5 minutes.
4. The seed script demonstrates the new capability end-to-end without manual steps.
5. No new "TODO" without an issue link.

---

## What this MVP foundation deliberately does NOT do

These are explicit non-goals for the initial scaffolding so we don't ship hand-waving:

- ❌ Real LLM-generated content out of the box without an API key (the local stub provider returns clearly-marked, deterministic placeholder output so the full pipeline can be exercised without spending API budget).
- ❌ Production observability stack (logs go to stdout).
- ❌ SSO, MFA, email flows.
- ❌ Real-time collaboration.
- ❌ Pricing module.
- ❌ Background job queue (sync MVP; clear migration seam).
- ❌ FedRAMP controls.

Everything not done is either explicitly stubbed with the right seam or documented above. The platform should still feel coherent, secure, and usable from the first `docker-compose up`.
