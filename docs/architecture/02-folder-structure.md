# MissionIQ — Folder Structure

```
MissionIQ/
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── docs/
│   ├── architecture/
│   │   ├── 01-system-architecture.md
│   │   ├── 02-folder-structure.md
│   │   ├── 03-database-schema.md
│   │   ├── 04-api-design.md
│   │   ├── 05-ui-design-system.md
│   │   ├── 06-security-architecture.md
│   │   └── 07-implementation-roadmap.md
│   └── setup/
│       └── local-development.md
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── seeds/
│   │   ├── seed.py                      # idempotent seed runner
│   │   ├── example_opportunity.json
│   │   └── example_documents/
│   │       ├── example_rfp.pdf
│   │       └── example_pws.docx
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_workspaces.py
│   │   ├── test_documents.py
│   │   ├── test_llm_router.py
│   │   └── test_rag.py
│   └── app/
│       ├── __init__.py
│       ├── main.py                      # FastAPI app factory
│       │
│       ├── core/                        # cross-cutting concerns
│       │   ├── __init__.py
│       │   ├── config.py                # Pydantic Settings (env-driven)
│       │   ├── db.py                    # async SQLAlchemy session
│       │   ├── security.py              # password hash, JWT encode/decode
│       │   ├── logging.py               # structured logging
│       │   ├── errors.py                # AppError + handlers
│       │   └── dependencies.py          # FastAPI Depends (CurrentUser, WorkspaceScope)
│       │
│       ├── models/                      # SQLAlchemy ORM models (1 file per aggregate)
│       │   ├── __init__.py
│       │   ├── base.py                  # Base, TimestampMixin, UUIDPk
│       │   ├── user.py
│       │   ├── workspace.py             # Workspace, TeamMember
│       │   ├── opportunity.py
│       │   ├── document.py              # Document, DocumentChunk
│       │   ├── market_intel.py          # MarketIntelSource, MarketIntelRecord, OpportunityMarketIntelLink
│       │   ├── company_profile.py       # CompanyProfile, Capability
│       │   ├── intelligence.py          # AIOutput, ComplianceRequirement, EvaluationCriterion, Risk
│       │   ├── chat.py                  # ChatThread, ChatMessage
│       │   └── audit.py                 # AuditLog
│       │
│       ├── schemas/                     # Pydantic v2 schemas (request/response)
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   ├── user.py
│       │   ├── workspace.py
│       │   ├── opportunity.py
│       │   ├── document.py
│       │   ├── market_intel.py
│       │   ├── company_profile.py
│       │   ├── intelligence.py
│       │   ├── chat.py
│       │   └── common.py                # Citation, Evidence, Pagination
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   └── v1/
│       │       ├── __init__.py          # APIRouter assembly
│       │       ├── auth.py
│       │       ├── users.py
│       │       ├── workspaces.py
│       │       ├── opportunities.py
│       │       ├── documents.py
│       │       ├── market_intel.py
│       │       ├── modules.py           # /opportunities/{id}/modules/{module_id}/run
│       │       ├── chat.py
│       │       ├── company_profile.py
│       │       ├── exports.py           # CSV exports (compliance, risk)
│       │       └── health.py
│       │
│       ├── services/                    # business logic (no HTTP)
│       │   ├── __init__.py
│       │   ├── auth_service.py
│       │   ├── workspace_service.py
│       │   ├── opportunity_service.py
│       │   ├── document_service.py      # orchestrates upload → extract → chunk → embed
│       │   ├── market_intel_service.py
│       │   ├── chat_service.py
│       │   ├── company_profile_service.py
│       │   ├── export_service.py
│       │   └── audit_service.py
│       │
│       ├── storage/                     # BlobStore abstraction
│       │   ├── __init__.py
│       │   ├── base.py                  # BlobStore protocol
│       │   ├── local.py                 # LocalBlobStore
│       │   └── s3.py                    # S3BlobStore (future)
│       │
│       ├── llm/                         # provider abstraction
│       │   ├── __init__.py
│       │   ├── base.py                  # LLMClient protocol, LLMResponse, EmbeddingClient
│       │   ├── router.py                # LLMRouter (selects provider per request)
│       │   ├── providers/
│       │   │   ├── __init__.py
│       │   │   ├── openai.py
│       │   │   ├── anthropic.py
│       │   │   ├── bedrock.py
│       │   │   ├── azure_openai.py
│       │   │   └── local_stub.py        # deterministic stub for tests / no-API-key dev
│       │   ├── prompts/                 # versioned prompts (YAML)
│       │   │   ├── capture/
│       │   │   │   ├── opportunity_summary.v1.yaml
│       │   │   │   ├── compliance_matrix.v1.yaml
│       │   │   │   ├── evaluation_criteria.v1.yaml
│       │   │   │   ├── requirement_breakdown.v1.yaml
│       │   │   │   ├── win_themes.v1.yaml
│       │   │   │   ├── capability_gaps.v1.yaml
│       │   │   │   ├── staffing_assumptions.v1.yaml
│       │   │   │   ├── proposal_outline.v1.yaml
│       │   │   │   ├── risk_register.v1.yaml
│       │   │   │   └── market_intel_summary.v1.yaml
│       │   │   └── chat/
│       │   │       └── analyst_assistant.v1.yaml
│       │   └── prompt_library.py        # loads + renders YAML prompts
│       │
│       ├── intelligence/                # platform-level intelligence core
│       │   ├── __init__.py
│       │   ├── registry.py              # ModuleRegistry
│       │   ├── base.py                  # BaseIntelligenceModule
│       │   ├── rag.py                   # RAGEngine (retrieve, rerank)
│       │   ├── citations.py             # CitationRef + validator
│       │   └── modules/
│       │       ├── __init__.py
│       │       └── capture/
│       │           ├── __init__.py
│       │           ├── opportunity_summary.py
│       │           ├── compliance_matrix.py
│       │           ├── evaluation_criteria.py
│       │           ├── requirement_breakdown.py
│       │           ├── win_themes.py
│       │           ├── capability_gaps.py
│       │           ├── staffing_assumptions.py
│       │           ├── proposal_outline.py
│       │           ├── risk_register.py
│       │           └── market_intel_summary.py
│       │
│       ├── ingestion/                   # document processing pipeline
│       │   ├── __init__.py
│       │   ├── pipeline.py              # run(document_id) orchestration
│       │   ├── extractors/
│       │   │   ├── __init__.py
│       │   │   ├── base.py
│       │   │   ├── pdf.py               # pypdf
│       │   │   ├── docx.py              # python-docx
│       │   │   └── txt.py
│       │   ├── chunker.py               # section-aware + token-bounded
│       │   └── embedder.py              # batch embed via EmbeddingClient
│       │
│       └── integrations/
│           ├── __init__.py
│           └── sam_gov/
│               ├── __init__.py
│               ├── client.py            # public API client
│               └── mapper.py            # → MarketIntelRecord
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── tsconfig.json
    ├── next.config.mjs
    ├── tailwind.config.ts
    ├── postcss.config.mjs
    ├── .eslintrc.json
    ├── public/
    │   └── logo-missioniq.svg
    └── src/
        ├── app/                         # Next.js App Router
        │   ├── layout.tsx               # root, fonts, theme
        │   ├── globals.css
        │   ├── page.tsx                 # redirect → /dashboard or /login
        │   ├── (auth)/
        │   │   ├── layout.tsx           # split-pane brand layout
        │   │   ├── login/page.tsx
        │   │   └── signup/page.tsx
        │   └── (app)/
        │       ├── layout.tsx           # PlatformShell (nav + topbar)
        │       ├── dashboard/page.tsx               # Executive Dashboard
        │       ├── workspaces/
        │       │   ├── page.tsx                     # Workspace List
        │       │   └── [workspaceId]/
        │       │       ├── settings/page.tsx
        │       │       ├── company-profile/page.tsx
        │       │       └── team/page.tsx
        │       ├── capture/                         # Capture Intelligence module group
        │       │   ├── layout.tsx                   # module-level nav (sub-tabs)
        │       │   ├── opportunities/
        │       │   │   ├── page.tsx                 # Opportunity List
        │       │   │   ├── new/page.tsx
        │       │   │   └── [opportunityId]/
        │       │   │       ├── page.tsx             # Opportunity Detail (briefing)
        │       │   │       ├── documents/page.tsx
        │       │   │       ├── summary/page.tsx
        │       │   │       ├── compliance/page.tsx
        │       │   │       ├── evaluation/page.tsx
        │       │   │       ├── requirements/page.tsx
        │       │   │       ├── win-themes/page.tsx
        │       │   │       ├── capabilities/page.tsx
        │       │   │       ├── staffing/page.tsx
        │       │   │       ├── outline/page.tsx
        │       │   │       ├── risks/page.tsx
        │       │   │       ├── market-intel/page.tsx
        │       │   │       └── assistant/page.tsx
        │       │   └── market-intel/
        │       │       ├── search/page.tsx
        │       │       └── records/page.tsx
        │       ├── operations/page.tsx              # stub: "Coming soon"
        │       ├── process/page.tsx                 # stub
        │       ├── risk/page.tsx                    # stub
        │       ├── performance/page.tsx             # stub
        │       ├── organizational/page.tsx          # stub
        │       └── settings/page.tsx
        │
        ├── components/                  # design system + composed components
        │   ├── ds/                      # primitives (no business logic)
        │   │   ├── Button.tsx
        │   │   ├── Card.tsx
        │   │   ├── Badge.tsx
        │   │   ├── Input.tsx
        │   │   ├── Select.tsx
        │   │   ├── Textarea.tsx
        │   │   ├── DataTable.tsx
        │   │   ├── KpiCard.tsx
        │   │   ├── Citation.tsx         # inline citation chip + hover-card
        │   │   ├── BriefingSection.tsx  # Exec Summary / Findings / Evidence / Actions
        │   │   ├── StatusPill.tsx       # green/amber/red
        │   │   ├── EmptyState.tsx
        │   │   ├── Skeleton.tsx
        │   │   └── Toast.tsx
        │   ├── shell/
        │   │   ├── PlatformShell.tsx
        │   │   ├── LeftNav.tsx          # module-aware
        │   │   ├── TopBar.tsx
        │   │   ├── WorkspaceSwitcher.tsx
        │   │   └── ModuleSwitcher.tsx
        │   ├── intelligence/
        │   │   ├── ExecutiveBriefing.tsx
        │   │   ├── ComplianceMatrixTable.tsx
        │   │   ├── RiskRegisterTable.tsx
        │   │   ├── EvaluationCriteriaList.tsx
        │   │   ├── WinThemesGrid.tsx
        │   │   ├── CapabilityGapMap.tsx
        │   │   └── EvidenceDrawer.tsx
        │   └── chat/
        │       ├── AssistantPanel.tsx
        │       └── MessageBubble.tsx
        │
        ├── lib/
        │   ├── api.ts                   # typed fetch client
        │   ├── auth.ts                  # token storage + refresh
        │   ├── workspace-context.tsx    # React context for selected workspace
        │   ├── types.ts                 # generated/handwritten DTOs
        │   ├── format.ts                # currency, date, NAICS labels
        │   └── citations.ts             # citation rendering helpers
        │
        └── styles/
            └── tokens.css               # CSS variables (colors, spacing)
```

## Conventions

- **One aggregate per model file** (e.g., `workspace.py` owns `Workspace` + `TeamMember`).
- **Routers are thin** — they unpack the request, call a service, return a schema. No business logic in `api/v1/*.py`.
- **Services receive a session and current user** — never `Request` or `Response`.
- **Modules are self-contained**: each `BaseIntelligenceModule` subclass declares its prompt id, output schema, and retrieval query in one place.
- **Frontend module groups** map 1:1 to platform module groups. Stubs exist today so the navigation is honest about what's coming.
