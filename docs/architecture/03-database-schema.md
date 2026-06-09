# MissionIQ — Database Schema

PostgreSQL 16 + `pgvector` extension. All primary keys are `UUID v4`. All tables include `created_at` and `updated_at` (`TIMESTAMPTZ`, server default `now()`).

> **Tenancy rule**: every workspace-scoped table has `workspace_id UUID NOT NULL` with `ON DELETE CASCADE` and a composite index `(workspace_id, ...)` on every common query path.

---

## 1. Entity Relationship Overview

```
user ─┬─< team_member >─┬─ workspace
      │                 │
      │                 ├─< opportunity ─┬─< document ─< document_chunk (embedding)
      │                 │                ├─< ai_output
      │                 │                ├─< compliance_requirement
      │                 │                ├─< evaluation_criterion
      │                 │                ├─< risk
      │                 │                ├─< chat_thread ─< chat_message
      │                 │                └─< opportunity_market_intel_link >─ market_intel_record
      │                 │
      │                 ├─── company_profile ─< capability
      │                 └─── market_intel_record (customer-licensed; workspace_id NOT NULL)
      │
      └─< audit_log

market_intel_source (catalog: SAM.gov, GovWin, …)
market_intel_record (workspace_id NULL = public, NOT NULL = customer-licensed)
```

---

## 2. Core Tables

### 2.1 `user`
| column | type | notes |
|--------|------|-------|
| id | UUID PK | |
| email | CITEXT UNIQUE NOT NULL | |
| password_hash | TEXT NOT NULL | argon2 |
| full_name | TEXT NOT NULL | |
| is_active | BOOLEAN NOT NULL DEFAULT TRUE | |
| is_superuser | BOOLEAN NOT NULL DEFAULT FALSE | |
| last_login_at | TIMESTAMPTZ | |
| created_at, updated_at | TIMESTAMPTZ | |

### 2.2 `workspace`
| column | type | notes |
|--------|------|-------|
| id | UUID PK | |
| name | TEXT NOT NULL | |
| slug | TEXT UNIQUE NOT NULL | url-safe |
| description | TEXT | |
| owner_user_id | UUID FK → user(id) | |
| settings_json | JSONB NOT NULL DEFAULT '{}'::jsonb | LLM defaults, data policies |
| created_at, updated_at | | |

### 2.3 `team_member`
| column | type | notes |
|--------|------|-------|
| id | UUID PK | |
| workspace_id | UUID FK → workspace(id) ON DELETE CASCADE | |
| user_id | UUID FK → user(id) ON DELETE CASCADE | |
| role | TEXT NOT NULL CHECK (role IN ('owner','admin','member','viewer')) | |
| invited_at, joined_at | TIMESTAMPTZ | |
| UNIQUE (workspace_id, user_id) | | |

### 2.4 `opportunity`
| column | type | notes |
|--------|------|-------|
| id | UUID PK | |
| workspace_id | UUID FK → workspace(id) ON DELETE CASCADE | |
| name | TEXT NOT NULL | |
| agency | TEXT | |
| sub_agency | TEXT | |
| contract_vehicle | TEXT | |
| solicitation_number | TEXT | |
| naics_code | TEXT | |
| psc_code | TEXT | |
| set_aside | TEXT | |
| due_date | TIMESTAMPTZ | |
| posted_date | TIMESTAMPTZ | |
| estimated_value_cents | BIGINT | int cents, currency = USD assumed |
| capture_stage | TEXT NOT NULL DEFAULT 'identification' CHECK (capture_stage IN ('identification','qualification','pursue','capture','proposal','submitted','awarded','lost','no-bid')) | |
| incumbent | TEXT | |
| notes | TEXT | |
| created_by_user_id | UUID FK → user(id) | |
| created_at, updated_at | | |

Indexes: `(workspace_id, capture_stage)`, `(workspace_id, due_date)`, `(workspace_id, agency)`.

### 2.5 `document`
| column | type | notes |
|--------|------|-------|
| id | UUID PK | |
| workspace_id | UUID FK → workspace(id) ON DELETE CASCADE | |
| opportunity_id | UUID FK → opportunity(id) ON DELETE CASCADE | |
| name | TEXT NOT NULL | original filename |
| doc_type | TEXT NOT NULL CHECK (doc_type IN ('rfp','rfi','sources_sought','pws','sow','soo','qasp','sections_l_m','evaluation_criteria','past_performance','capture_notes','internal_solution','other')) | |
| mime_type | TEXT NOT NULL | |
| size_bytes | BIGINT NOT NULL | |
| blob_key | TEXT NOT NULL | opaque key into BlobStore |
| sha256 | TEXT NOT NULL | dedupe + integrity |
| page_count | INT | populated post-extract |
| status | TEXT NOT NULL DEFAULT 'uploaded' CHECK (status IN ('uploaded','extracting','chunking','embedding','ready','failed')) | |
| error_message | TEXT | |
| uploaded_by_user_id | UUID FK → user(id) | |
| uploaded_at | TIMESTAMPTZ NOT NULL DEFAULT now() | |
| processed_at | TIMESTAMPTZ | |
| created_at, updated_at | | |

Indexes: `(workspace_id, opportunity_id)`, `(workspace_id, sha256)`.

### 2.6 `document_chunk`
| column | type | notes |
|--------|------|-------|
| id | UUID PK | |
| workspace_id | UUID NOT NULL | denormalized for query speed |
| document_id | UUID FK → document(id) ON DELETE CASCADE | |
| opportunity_id | UUID NOT NULL | denormalized |
| chunk_index | INT NOT NULL | order within document |
| page_start | INT | inclusive |
| page_end | INT | inclusive |
| section_path | TEXT | e.g. "Section L.3.1" |
| text | TEXT NOT NULL | |
| token_count | INT NOT NULL | |
| embedding | vector(1536) | pgvector; nullable until embedded |
| embedding_model | TEXT | provider:model:version |
| created_at | TIMESTAMPTZ | |

Indexes:
- `(workspace_id, document_id, chunk_index)`
- `ivfflat (embedding vector_cosine_ops)` (created after seed data exists)

### 2.7 `market_intel_source`
Static catalog of integrated sources.
| column | type | notes |
|--------|------|-------|
| id | TEXT PK | e.g. 'sam_gov', 'govwin', 'sf_crm' |
| display_name | TEXT NOT NULL | |
| classification | TEXT NOT NULL CHECK (classification IN ('public','customer_licensed','customer_uploaded')) | |
| auth_mode | TEXT NOT NULL CHECK (auth_mode IN ('none','api_key','oauth','customer_credentials')) | |
| enabled | BOOLEAN NOT NULL DEFAULT TRUE | |

Seeded with: SAM.gov (public/api_key), GovWin (customer_licensed/customer_credentials), Salesforce (customer_licensed/oauth), SharePoint (customer_licensed/oauth).

### 2.8 `market_intel_record`
| column | type | notes |
|--------|------|-------|
| id | UUID PK | |
| source_id | TEXT FK → market_intel_source(id) | |
| workspace_id | UUID FK → workspace(id) ON DELETE CASCADE | **NULL = public/shared**; NOT NULL = customer-licensed |
| external_id | TEXT NOT NULL | e.g. SAM Notice ID |
| source_url | TEXT | |
| title | TEXT NOT NULL | |
| agency | TEXT | |
| sub_agency | TEXT | |
| notice_type | TEXT | |
| naics_code | TEXT | |
| psc_code | TEXT | |
| set_aside | TEXT | |
| estimated_value_cents | BIGINT | |
| posted_date | TIMESTAMPTZ | |
| due_date | TIMESTAMPTZ | |
| incumbent | TEXT | |
| raw_json | JSONB NOT NULL DEFAULT '{}'::jsonb | full upstream payload |
| summary | TEXT | optional AI-summarized abstract |
| summary_embedding | vector(1536) | for cross-record retrieval |
| fetched_at | TIMESTAMPTZ | |
| created_at, updated_at | | |
| UNIQUE (source_id, external_id, COALESCE(workspace_id, '00000000-0000-0000-0000-000000000000'::uuid)) | | |

Indexes: `(source_id, workspace_id, due_date)`, `(agency, due_date)`.

### 2.9 `opportunity_market_intel_link`
| column | type | notes |
|--------|------|-------|
| id | UUID PK | |
| workspace_id | UUID NOT NULL | |
| opportunity_id | UUID FK → opportunity(id) ON DELETE CASCADE | |
| market_intel_record_id | UUID FK → market_intel_record(id) ON DELETE CASCADE | |
| linked_by_user_id | UUID FK → user(id) | |
| relevance | NUMERIC(4,3) | optional similarity score |
| notes | TEXT | |
| created_at | TIMESTAMPTZ | |
| UNIQUE (opportunity_id, market_intel_record_id) | | |

### 2.10 `company_profile`
One row per workspace.
| column | type | notes |
|--------|------|-------|
| id | UUID PK | |
| workspace_id | UUID UNIQUE FK → workspace(id) | |
| legal_name | TEXT | |
| duns | TEXT | |
| uei | TEXT | |
| cage_code | TEXT | |
| primary_naics | TEXT | |
| size_standard | TEXT | |
| certifications | TEXT[] | e.g. {'8(a)','SDVOSB','HUBZone'} |
| overview | TEXT | |
| differentiators | TEXT | |
| past_performance_summary | TEXT | |
| created_at, updated_at | | |

### 2.11 `capability`
| column | type | notes |
|--------|------|-------|
| id | UUID PK | |
| workspace_id | UUID NOT NULL | |
| company_profile_id | UUID FK → company_profile(id) ON DELETE CASCADE | |
| name | TEXT NOT NULL | |
| category | TEXT | e.g. 'Cloud','Cyber','PM','Data' |
| maturity | TEXT CHECK (maturity IN ('emerging','developing','mature','market-leading')) | |
| description | TEXT | |
| keywords | TEXT[] | for matching |
| evidence_links | TEXT[] | URLs / doc refs |
| created_at, updated_at | | |

### 2.12 `ai_output`
Generic record of every AI generation.
| column | type | notes |
|--------|------|-------|
| id | UUID PK | |
| workspace_id | UUID NOT NULL | |
| opportunity_id | UUID FK → opportunity(id) ON DELETE CASCADE | nullable for cross-opportunity outputs |
| module_id | TEXT NOT NULL | e.g. 'capture.opportunity_summary' |
| module_version | TEXT NOT NULL | e.g. 'v1' |
| prompt_id | TEXT NOT NULL | prompt template id |
| prompt_version | TEXT NOT NULL | |
| model_provider | TEXT NOT NULL | 'openai' \| 'anthropic' \| 'bedrock' \| 'azure_openai' \| 'local_stub' |
| model_name | TEXT NOT NULL | e.g. 'gpt-4.1-mini' |
| input_tokens | INT | |
| output_tokens | INT | |
| latency_ms | INT | |
| output_json | JSONB NOT NULL | module-specific schema |
| evidence_chunk_ids | UUID[] | references document_chunk.id |
| evidence_market_record_ids | UUID[] | references market_intel_record.id |
| status | TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok','insufficient_context','error')) | |
| generated_by_user_id | UUID FK → user(id) | |
| created_at | | |

Indexes: `(workspace_id, opportunity_id, module_id, created_at DESC)`.

### 2.13 `compliance_requirement`
Structured rows derived from the compliance-matrix module (also editable by user).
| column | type | notes |
|--------|------|-------|
| id | UUID PK | |
| workspace_id | UUID NOT NULL | |
| opportunity_id | UUID FK → opportunity(id) ON DELETE CASCADE | |
| ai_output_id | UUID FK → ai_output(id) | source generation; nullable for manual rows |
| requirement_code | TEXT | e.g. "L.3.1" |
| requirement_text | TEXT NOT NULL | |
| source_document_id | UUID FK → document(id) | |
| source_page | INT | |
| source_section | TEXT | |
| owner | TEXT | placeholder string |
| status | TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','in_progress','complete','n_a')) | |
| notes | TEXT | |
| created_at, updated_at | | |

### 2.14 `evaluation_criterion`
| column | type | notes |
|--------|------|-------|
| id | UUID PK | |
| workspace_id | UUID NOT NULL | |
| opportunity_id | UUID FK → opportunity(id) ON DELETE CASCADE | |
| ai_output_id | UUID FK → ai_output(id) | |
| factor | TEXT NOT NULL | |
| subfactor | TEXT | |
| importance | TEXT CHECK (importance IN ('most_important','important','less_important','equal','unspecified')) | |
| required_response_elements | TEXT[] | |
| source_document_id | UUID FK → document(id) | |
| source_page | INT | |
| source_section | TEXT | |
| created_at, updated_at | | |

### 2.15 `risk`
| column | type | notes |
|--------|------|-------|
| id | UUID PK | |
| workspace_id | UUID NOT NULL | |
| opportunity_id | UUID FK → opportunity(id) ON DELETE CASCADE | |
| ai_output_id | UUID FK → ai_output(id) | |
| title | TEXT NOT NULL | |
| category | TEXT CHECK (category IN ('technical','staffing','schedule','financial','security','compliance','competitive','transition','other')) | |
| description | TEXT | |
| source_document_id | UUID FK → document(id) | |
| source_page | INT | |
| impact | TEXT CHECK (impact IN ('low','medium','high','critical')) | |
| likelihood | TEXT CHECK (likelihood IN ('low','medium','high')) | |
| mitigation | TEXT | |
| owner | TEXT | |
| status | TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','mitigated','accepted','closed')) | |
| created_at, updated_at | | |

### 2.16 `chat_thread`
| column | type | notes |
|--------|------|-------|
| id | UUID PK | |
| workspace_id | UUID NOT NULL | |
| opportunity_id | UUID FK → opportunity(id) ON DELETE CASCADE | nullable for workspace-level chats |
| title | TEXT | |
| created_by_user_id | UUID FK → user(id) | |
| created_at, updated_at | | |

### 2.17 `chat_message`
| column | type | notes |
|--------|------|-------|
| id | UUID PK | |
| thread_id | UUID FK → chat_thread(id) ON DELETE CASCADE | |
| workspace_id | UUID NOT NULL | denormalized for filtering |
| role | TEXT NOT NULL CHECK (role IN ('user','assistant','system')) | |
| content | TEXT NOT NULL | |
| evidence_chunk_ids | UUID[] | |
| evidence_market_record_ids | UUID[] | |
| model_provider | TEXT | |
| model_name | TEXT | |
| input_tokens, output_tokens | INT | |
| status | TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok','insufficient_context','error')) | |
| created_at | | |

### 2.18 `audit_log`
| column | type | notes |
|--------|------|-------|
| id | UUID PK | |
| workspace_id | UUID | nullable for global events (e.g. signup) |
| actor_user_id | UUID FK → user(id) | nullable for system events |
| action | TEXT NOT NULL | dotted, e.g. 'opportunity.created' |
| target_type | TEXT | e.g. 'opportunity','document','ai_output' |
| target_id | UUID | |
| meta | JSONB NOT NULL DEFAULT '{}'::jsonb | |
| ip | INET | |
| user_agent | TEXT | |
| created_at | TIMESTAMPTZ NOT NULL DEFAULT now() | append-only |

Indexes: `(workspace_id, created_at DESC)`, `(actor_user_id, created_at DESC)`.

---

## 3. Standard Action Vocabulary (audit_log.action)

```
auth.signup                workspace.created            document.uploaded
auth.login                 workspace.updated            document.processed
auth.logout                workspace.member_added       document.deleted
auth.failed                workspace.member_removed     ai.module.run
                           opportunity.created          ai.module.failed
                           opportunity.updated          chat.message.sent
                           opportunity.deleted          export.compliance_csv
                                                        export.risk_csv
                                                        market_intel.search
                                                        market_intel.linked
```

---

## 4. Row-Level Security (Production)

```sql
-- Example for opportunity table
ALTER TABLE opportunity ENABLE ROW LEVEL SECURITY;
CREATE POLICY opp_ws_isolation ON opportunity
  USING (workspace_id = current_setting('app.workspace_id')::uuid);
```

In MVP local dev, RLS is **defined but not enforced** (the application layer is authoritative). In production, the request middleware sets `SET LOCAL app.workspace_id = '...'` per transaction and RLS becomes a defense-in-depth layer.

---

## 5. Embedding Dimensionality

Default `vector(1536)` matches OpenAI `text-embedding-3-small`. If a workspace is configured for Bedrock Titan (1024) or a local model with a different dimension, embeddings for that workspace are stored in a parallel table (`document_chunk_emb_1024`) — out of MVP scope, but the schema reserves room by keeping `embedding_model` per row.

---

## 6. Migrations

Managed by **Alembic**. Every migration file is timestamped and reversible. `alembic upgrade head` is run on container startup in dev; in production it runs as a separate job before app rollout.

The initial migration `0001_initial.py` creates all tables above + `CREATE EXTENSION IF NOT EXISTS vector` + `CREATE EXTENSION IF NOT EXISTS citext`.
