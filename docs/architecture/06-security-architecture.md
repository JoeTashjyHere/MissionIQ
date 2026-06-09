# MissionIQ — Security Architecture

> **Posture**: design today so we can deploy into AWS GovCloud and pursue FedRAMP Moderate later **without re-architecting**.
> **Scope of this document**: MVP-implementable controls + the controls we deliberately defer with a documented seam.

---

## 1. Threat Model (Abbreviated)

| Threat | Mitigation |
|--------|------------|
| Cross-tenant data leakage | Workspace-scoped queries enforced at service layer; Postgres RLS in prod; explicit denylist on all bulk endpoints |
| Credential theft | Argon2id password hashing, short-lived JWT access tokens (30m), rotating refresh tokens (14d) with server-side revocation list |
| Document exfiltration | Pre-signed URL pattern (BlobStore abstraction supports; local impl uses time-limited tokens), no public bucket |
| Prompt injection via uploaded docs | RAG retrieval-only, system prompt structurally separated from evidence, output schema validated server-side, citation enforcement |
| Foundation-model training on customer data | Provider configuration enforces no-training; contractual upstream; no logging of full prompts to third-party telemetry |
| Audit tampering | Append-only `audit_log`; in prod, separate WAL retention + write-only DB role |
| Unauthorized integration access (GovWin/CRM) | Customer-supplied credentials encrypted at rest, decrypted in-memory per request, never logged |
| Stolen access token | Short TTL + server-side refresh revocation; future MFA on sensitive actions |
| SQL injection | Pure parameterized queries via SQLAlchemy; no string SQL |
| XSS in AI output | All AI strings rendered as text, never `dangerouslySetInnerHTML`; markdown sanitized via `rehype-sanitize` |
| Open file upload abuse | MIME + magic-byte check, size cap (50 MB), AV scan hook (stub in MVP), per-workspace quota |
| Supply-chain | Pinned versions, `pip-audit` + `npm audit` in CI (added on first commit), no `curl | sh` installers |

---

## 2. Identity & Access

### 2.1 Authentication

- **Mechanism**: email + password.
- **Hashing**: Argon2id (`argon2-cffi`) with parameters tuned for ~250ms on dev hardware. Cost params live in config and are re-checked on login (auto-rehash on parameter upgrade).
- **Tokens**: JWT signed with HS256 in dev, **RS256 in prod** (key in AWS KMS / Secrets Manager).
  - `access_token`: 30 min, claims = `{ sub: user_id, ws: [workspace_ids], iat, exp, jti }`
  - `refresh_token`: 14 days, opaque random 256-bit, stored hashed in `refresh_token` table with `revoked_at`. Rotated on every use.
- **Lockout**: 10 failed logins per email / 15 minutes triggers a soft lockout (HTTP 429 with retry-after).
- **Password policy** (MVP defaults; configurable per workspace later): min 12 chars, must include 3 of {upper, lower, digit, symbol}, denylist of top-1000 common passwords.

**Future-ready**: an `IdentityProvider` enum exists from day one on `user.identity_provider`, defaulting to `'password'`. SSO (OIDC/SAML) and SCIM provisioning will set this field to `'oidc:okta'` etc.; no schema change needed.

### 2.2 Authorization

- **Workspace membership** is the primary access boundary.
- **Roles** (`team_member.role`): `owner` > `admin` > `member` > `viewer`.
  - `owner`: everything + delete workspace, manage billing (future).
  - `admin`: manage members, settings, integrations.
  - `member`: create/edit opportunities, documents, run modules.
  - `viewer`: read-only.
- **Permission checks** are centralized in `app.core.permissions` (`require(action, resource)`); routes call `require("opportunity.update", opportunity)`. Roles map to action sets in a single table — easy to extend to fine-grained per-resource ACLs without touching call sites.

### 2.3 Workspace Scope (Defense in Depth)

Layer 1 (application): every service function takes `workspace_id` and filters every query.
Layer 2 (request): middleware verifies `JWT.ws` contains the resolved `workspace_id`.
Layer 3 (database, prod): RLS policy on every workspace-scoped table reads `current_setting('app.workspace_id')`; the middleware sets it per transaction. If any layer fails, the data does not leak.

---

## 3. Data Protection

### 3.1 Classification (recap)

| Class | Where | Workspace-scoped? |
|-------|-------|-------------------|
| Public | SAM.gov records | No |
| Customer Uploaded | `document`, `document_chunk`, `ai_output`, `compliance_requirement`, `risk`, … | **Yes** |
| Customer Licensed | GovWin pulls, CRM exports → `market_intel_record` with `workspace_id` | **Yes** |
| Derived AI Output | `ai_output`, `chat_message` | **Yes** |

### 3.2 At Rest

- **Postgres** TDE in production (RDS / Aurora native). MVP local: filesystem-level only.
- **BlobStore** local impl writes under `./var/blobs/{workspace_id}/{document_id}/{blob_key}`. S3 impl uses SSE-KMS with customer-managed keys (per-workspace KMS key path planned, stubbed in BlobStore interface).
- **Secrets**: env vars in dev; AWS Secrets Manager / Parameter Store in prod. **Never** logged, **never** returned in API responses, **never** stored in git.
- **Customer integration credentials** (GovWin, CRM): stored encrypted with a per-workspace data key wrapped by a master KMS key. Decrypt only in-memory per request. Out of MVP scope to implement encryption; the table column (`secret_ciphertext`) and the `SecretsService` abstraction exist from day one.

### 3.3 In Transit

- **HTTPS only** in any non-local environment. HSTS preload eligibility once on a real domain.
- Backend ↔ DB: TLS required in prod (`sslmode=require`).
- Backend ↔ LLM providers: TLS 1.2+. Outbound egress is restricted via VPC endpoints (prod).

### 3.4 Data Retention & Deletion

- **Soft delete** on `opportunity` and `document` for 30 days, then hard delete (background job; out of MVP, but the `deleted_at` column is included for `document`).
- **Hard delete** purges blob + chunks + embeddings; the `audit_log` entry remains (action: `document.deleted`).
- **Workspace deletion**: cascades to all workspace-scoped tables; audit entries are aggregated into a retention bucket (future).

---

## 4. AI Security

### 4.1 No-Training Guarantee

- **OpenAI**: requests sent with `store=false` and via API keys on an **organization with training opt-out**. The platform refuses to start if `OPENAI_TRAINING_OPT_OUT_ACK=false`.
- **Anthropic**: API default is no training; documented in code.
- **AWS Bedrock**: customer-data not used for training; we configure the inference profile with `customer_data_logging=false` (planned).
- **Azure OpenAI**: deployment in customer-controlled subscription; abuse-monitoring opt-out required for FedRAMP path (documented).
- **Local stub provider**: used in tests and offline dev — no data leaves the host.

### 4.2 Prompt Injection Defense

- **Structural separation**: system prompt and evidence are concatenated with explicit delimiters and a final instruction reminding the model to treat evidence as data, not instructions.
- **No tool use** in MVP modules (eliminates a major injection vector). The chat assistant is retrieval-only.
- **Output validation**: every module's response is parsed against a Pydantic schema; malformed responses return `status='error'` and are not persisted as content.
- **Citation enforcement**: schemas require `citations: []`; if empty, output is marked `insufficient_context` (or `error`) regardless of model text.
- **Rendering hygiene**: AI output rendered as plain text or sanitized markdown only.

### 4.3 Telemetry Hygiene

- We **log token counts, model id, prompt id, prompt version, latency** in `ai_output`.
- We **do not** send full prompts or completions to third-party APM/observability without explicit opt-in (and never for customer-tagged workspaces).
- The structured logger has a `sensitive_fields` denylist that scrubs `password`, `token`, `secret`, `authorization`, and the configurable `customer_text_fields`.

---

## 5. Document Upload Pipeline Security

1. **Size cap** (50 MB MVP) enforced before bytes hit disk (FastAPI `request.stream()` checked).
2. **MIME + magic-byte check**: `python-magic` validates the declared MIME against actual bytes.
3. **Extension allowlist**: `.pdf`, `.docx`, `.txt` only.
4. **Hash on write** (sha256) for dedupe + integrity. Re-uploading the same hash returns the existing `document_id`.
5. **AV scan hook**: `app.ingestion.av.scan(blob_key)` returns `clean | infected | error`. MVP impl is a stub returning `clean`; prod wires ClamAV / managed AV. Infected files are quarantined (not deleted) and the upload returns 422 with a code.
6. **Quotas**: per-workspace storage cap (default 5 GB, configurable). Soft 80% warning, hard block at 100%.
7. **Tenant isolation**: blob keys are derived from `workspace_id`, and the `BlobStore.read(key)` enforces a prefix match against the calling scope.

---

## 6. Audit Logging

- **Append-only** `audit_log` table.
- **Required fields**: `workspace_id`, `actor_user_id`, `action`, `target_type/id`, `meta`, `ip`, `user_agent`, `created_at`.
- **Standard vocabulary**: see Database Schema doc §3.
- **Surfaced in UI**: admins see `/workspaces/{id}/audit` with filters. AI outputs link directly to their generating audit entry.
- **Tamper-evidence path**: in prod, daily Merkle-root snapshot of `audit_log` is signed and stored separately (future). The current schema supports this with an immutable `id, created_at` pair.

---

## 7. Network & Deployment Hardening (Prod, Out of MVP Scope)

- All inbound HTTPS via ALB; backend is private.
- Outbound restricted to known LLM/integration domains via VPC endpoints + egress allowlist.
- WAF in front of ALB (AWS WAF managed rule sets, including ATP for `/auth/*`).
- Secrets via Secrets Manager; rotation policy on integration credentials.
- IAM least privilege: each service has its own role; no shared admin keys.

The MVP local `docker-compose.yml` exposes only the frontend (3000) and backend (8000) on `127.0.0.1` by default.

---

## 8. Compliance Alignment (Forward-Looking)

| Control family (NIST 800-53 / FedRAMP Moderate) | MVP alignment |
|--------------------------------------------------|---------------|
| AC (Access Control) | Workspace scoping, RBAC, planned RLS |
| AU (Audit & Accountability) | `audit_log` standardized vocabulary |
| IA (Identification & Authentication) | Argon2id, JWT, rotation, planned MFA/SSO |
| SC (System and Communications Protection) | TLS everywhere, KMS-ready, network segmentation planned |
| SI (System and Information Integrity) | Input validation, output schema validation, AV scan hook |
| CM (Configuration Management) | Versioned migrations, pinned deps |
| CP (Contingency Planning) | DB backups (RDS prod), restorable docker-compose local |
| AT (Awareness & Training) | Out of code scope |

This is **alignment**, not certification. The MVP does not implement formal FedRAMP controls; it avoids choices that would block them.

---

## 9. Security Checklist for Every New Feature

When adding a new endpoint or module, the developer must answer:

1. Does this require a `WorkspaceScope` dependency? (Default: **yes**.)
2. Are all DB queries filtered by `workspace_id`?
3. Are inputs validated by a Pydantic schema with explicit field constraints?
4. Is the action recorded in `audit_log` (if it mutates state or accesses sensitive data)?
5. Does it touch a foundation model? If yes, does the prompt go through `PromptLibrary` and use grounded evidence?
6. Does it return citations for every AI claim?
7. Are errors mapped to safe user-facing messages (no stack traces, no DB errors leaked)?

A code-review checklist file (`docs/security-checklist.md`) carries this list and is referenced from `CONTRIBUTING.md` (future).
