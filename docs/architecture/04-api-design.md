# MissionIQ — API Design

Base URL: `/api/v1`
Content-Type: `application/json` (multipart for uploads)
Auth: `Authorization: Bearer <access_token>`

All responses use the envelope conventions below. All errors use RFC 7807 problem details with a MissionIQ extension.

---

## 1. Conventions

### 1.1 Pagination

```http
GET /api/v1/opportunities?limit=25&cursor=<opaque>
```

Response:
```json
{
  "items": [ ... ],
  "next_cursor": "eyJpZCI6Ii4uLiJ9",
  "total_estimate": 132
}
```

### 1.2 Error envelope (RFC 7807 + extension)

```json
{
  "type": "https://missioniq.dev/errors/workspace-not-found",
  "title": "Workspace not found",
  "status": 404,
  "detail": "Workspace 'abc' does not exist or you do not have access.",
  "request_id": "req_01HZ...",
  "code": "workspace.not_found"
}
```

### 1.3 IDs

All resource IDs are UUIDs. Slugs may be used in URLs for workspaces (`/workspaces/{slug-or-id}`).

### 1.4 Workspace scoping

Workspace ID is **never trusted from the body**. It is resolved from:
1. The URL path segment (e.g. `/workspaces/{workspace_id}/opportunities`), or
2. The `X-Workspace-Id` header for endpoints not nested under a workspace path, or
3. The user's currently selected workspace stored server-side (fallback).

Membership is verified by a `WorkspaceScope` dependency before any handler runs.

### 1.5 Idempotency

Mutating endpoints accept `Idempotency-Key: <uuid>` and store the response for 24h to make retries safe.

---

## 2. Auth & Users

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/signup` | Register a new user. Body: `{ email, password, full_name }`. Returns `{ access_token, refresh_token, user }`. |
| `POST` | `/auth/login` | Body: `{ email, password }`. Returns tokens + user. |
| `POST` | `/auth/refresh` | Body: `{ refresh_token }`. Returns new access token. |
| `POST` | `/auth/logout` | Revokes refresh token. |
| `GET`  | `/users/me` | Current user with workspace memberships. |
| `PATCH`| `/users/me` | Update `full_name`, change password. |

JWT access token: 30 min. Refresh token: 14 days, rotating, server-side revocation table.

---

## 3. Workspaces & Team

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/workspaces` | List workspaces the current user belongs to. |
| `POST` | `/workspaces` | Create `{ name, slug?, description? }`. Creator becomes owner. |
| `GET`  | `/workspaces/{id}` | Get workspace details. |
| `PATCH`| `/workspaces/{id}` | Update name/description/settings. |
| `DELETE` | `/workspaces/{id}` | Owner-only. |
| `GET`  | `/workspaces/{id}/members` | List members. |
| `POST` | `/workspaces/{id}/members` | Invite `{ email, role }`. |
| `PATCH`| `/workspaces/{id}/members/{member_id}` | Change role. |
| `DELETE`| `/workspaces/{id}/members/{member_id}` | Remove member. |
| `GET`  | `/workspaces/{id}/company-profile` | Get profile (auto-created with workspace). |
| `PUT`  | `/workspaces/{id}/company-profile` | Update profile. |
| `GET`  | `/workspaces/{id}/capabilities` | List capabilities. |
| `POST` | `/workspaces/{id}/capabilities` | Add capability. |
| `PATCH`| `/workspaces/{id}/capabilities/{cap_id}` | Update. |
| `DELETE`| `/workspaces/{id}/capabilities/{cap_id}` | Remove. |

---

## 4. Opportunities

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/workspaces/{ws_id}/opportunities` | Filterable: `?stage=&agency=&due_before=&q=` |
| `POST` | `/workspaces/{ws_id}/opportunities` | Create. |
| `GET`  | `/workspaces/{ws_id}/opportunities/{opp_id}` | Detail. |
| `PATCH`| `/workspaces/{ws_id}/opportunities/{opp_id}` | Update. |
| `DELETE`| `/workspaces/{ws_id}/opportunities/{opp_id}` | Delete. |
| `GET`  | `/opportunities/{opp_id}/overview` | KPI roll-up: doc count, AI runs, risks, compliance %. Convenience read-only. |

---

## 5. Documents

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/opportunities/{opp_id}/documents` | `multipart/form-data` with `file` and `doc_type`. Returns document record with `status='uploaded'`; pipeline runs as background task. |
| `GET`  | `/opportunities/{opp_id}/documents` | List. |
| `GET`  | `/documents/{doc_id}` | Detail incl. processing status. |
| `GET`  | `/documents/{doc_id}/raw` | Download original file (stream from BlobStore). |
| `GET`  | `/documents/{doc_id}/chunks?limit=&offset=` | Inspect chunks (debug/admin). |
| `POST` | `/documents/{doc_id}/reprocess` | Re-run extraction + embedding. |
| `DELETE`| `/documents/{doc_id}` | Soft-delete: blob + chunks purged, audit retained. |

---

## 6. Market Intelligence

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/market-intel/sources` | List configured sources (catalog). |
| `GET`  | `/market-intel/search?source=sam_gov&q=&naics=&agency=&posted_after=&due_before=&limit=` | Live or cached search. Public sources require no body. |
| `GET`  | `/market-intel/records/{record_id}` | Detail. |
| `POST` | `/workspaces/{ws_id}/market-intel/import` | Upsert records into workspace context (manual save). Body: `{ source_id, external_ids: [] }`. |
| `POST` | `/opportunities/{opp_id}/market-intel-links` | Link `{ market_intel_record_id, notes? }`. |
| `GET`  | `/opportunities/{opp_id}/market-intel-links` | List linked records. |
| `DELETE`| `/opportunities/{opp_id}/market-intel-links/{link_id}` | Unlink. |

> GovWin requires customer credentials supplied at `/workspaces/{ws_id}/integrations/govwin` (separate doc; out of MVP). The interface is identical.

---

## 7. Intelligence Modules (Capture)

The module registry exposes a single uniform interface:

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/modules` | All registered modules with metadata (id, group, label, output_schema). |
| `GET`  | `/modules/{module_id}` | Single module spec. |
| `POST` | `/opportunities/{opp_id}/modules/{module_id}/run` | Generate. Body optional `{ force?: bool, model_override?: string }`. Returns the new `ai_output` record. |
| `GET`  | `/opportunities/{opp_id}/modules/{module_id}/latest` | Most recent output for this module. |
| `GET`  | `/opportunities/{opp_id}/modules/{module_id}/history?limit=` | Versions. |

### Convenience structured-views (also used for editing / CSV export):

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/opportunities/{opp_id}/compliance-requirements` | List rows. |
| `PATCH`| `/compliance-requirements/{id}` | Update owner/status/notes. |
| `POST` | `/opportunities/{opp_id}/compliance-requirements` | Manual add. |
| `GET`  | `/opportunities/{opp_id}/evaluation-criteria` | List. |
| `GET`  | `/opportunities/{opp_id}/risks` | List. |
| `PATCH`| `/risks/{id}` | Update mitigation/owner/status. |
| `POST` | `/opportunities/{opp_id}/risks` | Manual add. |

### Module IDs (MVP — Capture group)

```
capture.opportunity_summary
capture.compliance_matrix
capture.evaluation_criteria
capture.requirement_breakdown
capture.win_themes
capture.capability_gaps
capture.staffing_assumptions
capture.proposal_outline
capture.risk_register
capture.market_intel_summary
```

Reserved groups (future): `operations.*`, `process.*`, `risk.*`, `performance.*`, `organizational.*`, `market.*`.

---

## 8. Chat (Intelligence Assistant)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat/threads` | `{ workspace_id, opportunity_id?, title? }` → new thread. |
| `GET`  | `/chat/threads` | List threads in workspace (filter by opp). |
| `GET`  | `/chat/threads/{thread_id}/messages?limit=` | Pagination. |
| `POST` | `/chat/threads/{thread_id}/messages` | `{ content }`. Returns `{ user_message, assistant_message }`. The assistant message includes `evidence_chunk_ids`, `evidence_market_record_ids`, `status`. |
| `DELETE`| `/chat/threads/{thread_id}` | Delete thread. |

---

## 9. Exports

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/opportunities/{opp_id}/exports/compliance.csv` | CSV stream. |
| `GET`  | `/opportunities/{opp_id}/exports/risks.csv` | CSV stream. |
| `GET`  | `/opportunities/{opp_id}/exports/proposal-outline.docx` | (future) |

---

## 10. Audit

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/workspaces/{ws_id}/audit?actor=&action=&from=&to=&limit=&cursor=` | Admin-only. |

---

## 11. Health & Meta

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Liveness. |
| `GET`  | `/health/ready` | Readiness (DB + storage). |
| `GET`  | `/meta/version` | Build info. |

---

## 12. Standard Response Shapes

### 12.1 `AIOutputResponse`

```json
{
  "id": "uuid",
  "module_id": "capture.opportunity_summary",
  "module_version": "v1",
  "status": "ok",
  "model": { "provider": "openai", "name": "gpt-4.1-mini" },
  "tokens": { "input": 4231, "output": 812 },
  "latency_ms": 5340,
  "output": { /* module-specific schema */ },
  "citations": [
    {
      "type": "document_chunk",
      "id": "uuid",
      "document_id": "uuid",
      "document_name": "RFP_W912DY-25-R-0042.pdf",
      "page_start": 12,
      "page_end": 12,
      "section_path": "Section L.3.1",
      "snippet": "The Contractor shall provide..."
    },
    {
      "type": "market_intel_record",
      "id": "uuid",
      "source_id": "sam_gov",
      "external_id": "W912DY25R0042",
      "source_url": "https://sam.gov/opp/...",
      "title": "Mission Operations Support"
    }
  ],
  "generated_at": "2026-06-09T14:22:00Z",
  "generated_by": { "id": "uuid", "full_name": "Alex Park" }
}
```

### 12.2 Module-specific output schemas (excerpt)

`capture.opportunity_summary`:
```json
{
  "mission_need": "string",
  "scope_summary": "string",
  "key_services": ["string"],
  "deliverables": ["string"],
  "timeline": { "period_of_performance": "string", "milestones": ["string"] },
  "risks": ["string"],
  "pursue_indicators": ["string"],
  "no_pursue_indicators": ["string"],
  "executive_summary": "string",
  "key_findings": ["string"],
  "recommended_actions": ["string"]
}
```

`capture.compliance_matrix`:
```json
{
  "requirements": [
    {
      "requirement_code": "L.3.1",
      "requirement_text": "string",
      "source": { "document_id": "uuid", "page": 12, "section": "L.3.1" },
      "category": "technical|management|past_performance|pricing|other",
      "must_have": true
    }
  ]
}
```

(Full schemas are owned by each module and validated server-side before persistence.)

---

## 13. Rate Limits (MVP)

| Scope | Limit |
|-------|-------|
| `/auth/login`, `/auth/signup` | 10 / min / IP |
| `/modules/*/run` | 20 / hour / workspace |
| Everything else | 600 / min / user |
