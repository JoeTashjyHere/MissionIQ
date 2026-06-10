# MissionIQ Demo Guide

## Apex Federal Solutions Showcase

MissionIQ ships with a fully synthetic demonstration environment — **Apex Federal Solutions** — a mid-sized federal technology and operations contractor. All agencies, pursuits, competitors, and content are fictional.

### Quick start (one command)

```bash
cd backend
python -m seeds.seed --apex
```

Docker Compose runs this automatically on first startup (`--apex --if-empty`).

### Demo credentials

| Role | Email | Password |
|------|-------|----------|
| Administrator (recommended) | sarah.mitchell@apexfederal.demo | MissionIQ!Demo2026 |
| Capture Director | michael.reynolds@apexfederal.demo | MissionIQ!Demo2026 |
| Proposal Manager | jennifer.carter@apexfederal.demo | MissionIQ!Demo2026 |
| Capture Analyst | david.kim@apexfederal.demo | MissionIQ!Demo2026 |
| BD Associate | emily.turner@apexfederal.demo | MissionIQ!Demo2026 |

**Workspace slug:** `apex-federal`

---

## 5-minute walkthrough

1. **Sign in** as Sarah Mitchell → lands on Dashboard.
2. **Open** Capture Intelligence → Opportunities — six pursuits (four completed, two active).
3. **Flagship active pursuit:** National Energy Operations Agency → *Workforce Services Modernization*.
4. **Win Strategy** — gate-review synthesis with historical proposal evidence.
5. **Executive Brief** — one-screen leadership package.
6. **Knowledge → Proposal Repository** — 24+ extracted intelligence assets with win/loss patterns.
7. **Outcomes** — workspace track record (42 pursuits, ~57% win rate on decided competitions).

**Key message:** MissionIQ turns federal growth work into institutional intelligence — not document storage.

---

## 10-minute walkthrough

Add to the 5-minute flow:

1. **Customer DNA** on the flagship pursuit — who the customer is and what they measure.
2. **Capability Match** — seller × customer fit with reusable win themes.
3. **Gate Review** on a completed win (CMS Citizen Engagement) — scored decision package.
4. **Pursuit Memory** on flagship — similar pursuits and recalled patterns.
5. **Knowledge Graph** — agencies, capabilities, competitors, win themes accumulated over time.
6. **Governance Hub** on flagship — comments, approvals, overrides, assumption validations.
7. **Integrations → Connectors** — Salesforce, SharePoint, Local Repository (connected) with sync history.

---

## Investor walkthrough (15 minutes)

**Story arc:** MissionIQ is the institutional memory layer for federal growth.

| Stop | Screen | Talking point |
|------|--------|---------------|
| 1 | Dashboard | Pipeline visibility without spreadsheets |
| 2 | Win Strategy (NEOA) | Flagship synthesis — not summarization |
| 3 | Executive Brief | Boardroom-ready in one screen |
| 4 | Outcome Intelligence | Closed learning loop — observed patterns, not causation |
| 5 | Proposal Repository | Proposal knowledge as reusable assets |
| 6 | Knowledge Graph | Graph strengthens with every pursuit |
| 7 | Connectors + Automation | Ingest → automate → decide |

**Differentiation:** Epistemic honesty (Evidence / Inference / Assumption), governance without mutating AI outputs, outcome-weighted institutional memory.

---

## Design partner walkthrough

Focus on workflow realism:

1. Log in as **Jennifer Carter** (reviewer) — review Win Strategy comments and approval state.
2. Log in as **Michael Reynolds** (approver) — decision timeline, overrides, gate review.
3. Log in as **David Kim** (contributor) — generate intelligence, submit for review.
4. Compare **completed win** (CMS) vs **completed loss** (NASA service desk) — outcome linkage on proposal assets.
5. **No-bid pursuit** (DMS) — honest capability gap assessment.

---

## Recommended demo screens

| Priority | Route | Why |
|----------|-------|-----|
| ★★★ | `/capture/opportunities` → NEOA pursuit → Win Strategy | Flagship synthesis |
| ★★★ | Same → Executive Brief | Leadership decision package |
| ★★★ | `/knowledge` | Proposal intelligence, not files |
| ★★★ | `/outcomes` | Win/loss learning loop |
| ★★ | NEOA → Memory → Knowledge Graph | Institutional memory |
| ★★ | NEOA → Governance Hub | Human-in-the-loop |
| ★★ | `/integrations/connectors` | Connector + automation story |
| ★ | CMS won pursuit → Gate Review | Completed pursuit proof |
| ★ | NASA lost pursuit → Outcome rationale | Honest loss learning |

---

## Load Demo Workspace (UI)

Administrators can click **Load Demo Workspace** on the Dashboard. The operation is idempotent — safe to run multiple times. It refreshes synthetic data without external integrations.

API: `POST /api/v1/demo/load` (administrator role required).

---

## What is pre-populated

- **Company profile** — Apex Federal Solutions with 8 core capabilities
- **6 showcase pursuits** — full intelligence modules on each
- **38 historical pursuits** — outcome depth for workspace analytics
- **24 proposal assets** — executive summaries, win themes, transitions, staffing, past performance, risk mitigation
- **3 connectors** — Salesforce, SharePoint, Local Repository (connected)
- **Governance activity** — comments, reviews, approvals, overrides on flagship pursuit
- **Automation history** — successful connector-triggered runs on flagship

No document uploads required for the demo experience.
