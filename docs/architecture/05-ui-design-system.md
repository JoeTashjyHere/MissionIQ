# MissionIQ — UI Design System

> The UI must read as **executive intelligence**, not as a consumer AI product.
> Every screen should look like something a Capture VP, PM, or contracting officer would screenshot into a Monday briefing deck.

---

## 1. Brand Foundation

| Attribute | Manifests as |
|-----------|--------------|
| Confident | Strong typographic hierarchy, decisive language, no exclamation points |
| Analytical | Tabular density, KPI cards, evidence-first layouts |
| Trustworthy | Consistent spacing, no jitter, source citations everywhere |
| Executive | Briefing-style pages: Executive Summary → Key Findings → Evidence → Actions |
| Mission-focused | Action verbs ("Pursue", "Submit", "Mitigate"), capture-domain vocabulary |
| Secure | Workspace badge persistent, classification labels visible, audit affordances |
| Auditable | Every AI output shows model, time, source citations, "View evidence" affordance |
| Outcome-driven | Pursue/No-Pursue indicators, win-theme alignment, risk posture |

**Forbidden**: gradient hero sections, illustrated mascots, emoji UI, AI-first chat home screens, "Magic"/"Sparkle" affordances.

---

## 2. Color Tokens

CSS custom properties live in `src/styles/tokens.css`; Tailwind reads them via `theme.extend.colors`.

### 2.1 Primary

| Token | Hex | Usage |
|-------|-----|-------|
| `--miq-navy-900` | `#0A1F33` | Top bar, primary headings, dark surfaces |
| `--miq-navy-800` | `#102A44` | Left nav background |
| `--miq-navy-700` | `#1B3957` | Hover states on dark surfaces |
| `--miq-charcoal-900` | `#1A1D21` | Body text on light surfaces |
| `--miq-charcoal-700` | `#3A3F45` | Secondary text |
| `--miq-charcoal-500` | `#6B7079` | Muted text, metadata |
| `--miq-charcoal-300` | `#C3C7CD` | Borders, dividers |
| `--miq-charcoal-100` | `#EEF1F4` | Subtle backgrounds |
| `--miq-white` | `#FFFFFF` | Page surfaces |
| `--miq-canvas` | `#F6F8FB` | App background |

### 2.2 Accent

| Token | Hex | Usage |
|-------|-----|-------|
| `--miq-steel-700` | `#2A5A8C` | Primary buttons, links, active nav |
| `--miq-steel-500` | `#3F7AB8` | Default interactive |
| `--miq-steel-300` | `#A5C0DE` | Focus rings, subtle highlights |
| `--miq-teal-700` | `#1E6F73` | Module badge: Intelligence/Insight |
| `--miq-teal-500` | `#3FA2A6` | Secondary accent, tag color |
| `--miq-teal-100` | `#E1F1F2` | Soft callouts |

### 2.3 Status

| Token | Hex | Usage |
|-------|-----|-------|
| `--miq-status-green` | `#2F7D55` | Pursue, compliant, on track |
| `--miq-status-green-bg` | `#E6F2EB` | Pill background |
| `--miq-status-amber` | `#B5780C` | Watch, partial, schedule risk |
| `--miq-status-amber-bg` | `#FBF1DC` | |
| `--miq-status-red` | `#A8302E` | No-pursue, non-compliant, critical risk |
| `--miq-status-red-bg` | `#F7E3E2` | |
| `--miq-status-info` | `#2A5A8C` | Informational |

### 2.4 Semantic mapping

```css
--miq-bg-app: var(--miq-canvas);
--miq-bg-surface: var(--miq-white);
--miq-bg-elevated: var(--miq-white);
--miq-text-primary: var(--miq-charcoal-900);
--miq-text-secondary: var(--miq-charcoal-700);
--miq-text-muted: var(--miq-charcoal-500);
--miq-border: var(--miq-charcoal-300);
--miq-border-subtle: var(--miq-charcoal-100);
--miq-focus: var(--miq-steel-300);
--miq-link: var(--miq-steel-700);
```

---

## 3. Typography

**Font stack**:
- Display / UI: **Inter** (variable) — fallback: `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`
- Numeric/Data: **Inter** with `font-feature-settings: "tnum", "lnum"`
- Mono (citations, IDs, code): **JetBrains Mono** — fallback: `ui-monospace, SFMono-Regular, Menlo, monospace`

**Type scale** (rem on 16px base):

| Token | Size | Line | Weight | Use |
|-------|------|------|--------|-----|
| `display` | 2.25 | 1.15 | 600 | Page hero rare; reserved |
| `h1` | 1.75 | 1.2 | 600 | Page title |
| `h2` | 1.375 | 1.25 | 600 | Section title |
| `h3` | 1.125 | 1.3 | 600 | Card title |
| `h4` | 1.0 | 1.4 | 600 | Sub-section |
| `body` | 0.9375 (15px) | 1.55 | 400 | Default body |
| `body-sm` | 0.8125 (13px) | 1.5 | 400 | Metadata |
| `mono` | 0.8125 | 1.5 | 400 | Citations, IDs |
| `eyebrow` | 0.75 | 1.2 | 600 | Uppercase section labels |

Eyebrows are `text-transform: uppercase; letter-spacing: 0.08em;` and `color: var(--miq-text-muted)`. They are heavily used because briefings live or die on hierarchy.

---

## 4. Spacing & Layout

- **Base unit**: 4px. Use Tailwind 1/2/3/4/6/8/10/12 (i.e. 4/8/12/16/24/32/40/48 px).
- **Page max width**: `max-w-[1440px]` centered.
- **Content max width**: `max-w-[1120px]` for briefing pages; tables go full width.
- **Vertical rhythm**: section gap `24px`, card padding `24px`, page padding `32px`.
- **Radii**: `--radius-sm: 6px`, `--radius-md: 10px`, `--radius-lg: 14px`. Cards use `md`. No fully rounded "candy" pills (max `9999px` only on Status Pills and Badge tokens).
- **Shadows**: minimal. `--shadow-card: 0 1px 2px rgba(10,31,51,0.04), 0 1px 1px rgba(10,31,51,0.06);` Elevated dialogs use `0 12px 32px rgba(10,31,51,0.12)`.

---

## 5. Platform Shell

```
┌──────────────────────────────────────────────────────────────────────────┐
│  TopBar:  [MissionIQ]   [Workspace ▾]                  [⌘K]  [User ▾]   │  56px, navy-900
├──────────┬───────────────────────────────────────────────────────────────┤
│ LeftNav  │  Page content                                                  │
│ 248px    │                                                                │
│  navy-800│  ┌ Page header (title, breadcrumb, primary action) ─────────┐ │
│          │  └──────────────────────────────────────────────────────────┘ │
│  Module  │  ┌ Briefing or table or grid ────────────────────────────────┐│
│  Group   │  │                                                           ││
│  Tabs    │  └───────────────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────────────┘
```

### LeftNav structure (always shows the platform, then the active module's pages)

```
MissionIQ
─────────
Dashboard

CAPTURE INTELLIGENCE          ← module group eyebrow
  Opportunities
  Market Intelligence
  Assistant

OPERATIONS INTELLIGENCE        ← stub group; disabled chevron
PROCESS INTELLIGENCE           ← stub
PERFORMANCE INTELLIGENCE       ← stub
RISK INTELLIGENCE              ← stub
ORGANIZATIONAL INTELLIGENCE    ← stub
MARKET INTELLIGENCE            ← stub
─────────
WORKSPACE
  Company Profile
  Team
  Settings
  Audit
```

When the user opens an opportunity, the LeftNav second-level swaps to opportunity sub-navigation (Summary, Compliance, Evaluation, Requirements, Win Themes, Capabilities, Staffing, Outline, Risks, Market Intel, Assistant, Documents). The platform crumb stays present so the user always knows they are inside MissionIQ → Capture Intelligence → Opportunity.

### TopBar

- Logo wordmark (small, mono-color).
- **Workspace switcher** (defines tenant scope; cannot be hidden).
- Global search (`⌘K`) — placeholder in MVP.
- User menu (account, sign out).

---

## 6. Primitives (`src/components/ds`)

| Component | Variants | Notes |
|-----------|----------|-------|
| `Button` | `primary`, `secondary`, `ghost`, `danger`; sizes `sm`, `md`, `lg` | Loading state shows spinner + label, never replaces label entirely |
| `Card` | default, `subtle` (no border), `outline` | 24px padding, `--shadow-card` |
| `Badge` | `default`, `info`, `teal`, `neutral` | Module/category labels |
| `StatusPill` | `green`, `amber`, `red`, `info`, `neutral` | Always paired with a textual label |
| `Input`, `Textarea`, `Select`, `Checkbox`, `RadioGroup` | — | 40px height, 1px border, focus ring `--miq-focus` |
| `DataTable` | sticky header, zebra `off`, hover row, optional row selection, dense mode | Empty state slot |
| `KpiCard` | label, value, delta (+/-), trend sparkline (placeholder) | Numeric font: tabular |
| `Citation` | inline `[1]` chip + hover-card with snippet & link to evidence drawer | Required component for any AI-rendered text |
| `BriefingSection` | header + slots for `executive_summary`, `key_findings`, `evidence`, `actions` | Canonical layout for module pages |
| `EmptyState` | icon (stroked, not filled), title, description, primary CTA | Used aggressively when modules haven't run |
| `Skeleton` | line / block / card | Loading state for everything |
| `Toast` | info / success / warning / error | Bottom-right, 4s default |
| `Drawer` | right-side, 480-720px | Used for Evidence Drawer, document preview |
| `Modal` | center, max 640px wide | Confirmations only |

### 6.1 Citation behavior

Citations are inline chips like `[1]` that:
- Render as `mono` font, `--miq-steel-700` text, underline on hover.
- Open a hover-card with: document name, page, section, 3-line snippet, "Open evidence" button.
- "Open evidence" opens the Evidence Drawer with the full chunk highlighted in context.

**Rule**: a frontend renderer **must refuse** to display an AI claim without at least one citation chip attached. The renderer surfaces an "Unsupported claim" warning in dev mode.

---

## 7. Briefing Page Pattern (every module page uses this)

```
┌─────────────────────────────────────────────────────────────────────┐
│ EYEBROW: Capture Intelligence · Opportunity Summary                  │
│ H1: Mission Operations Support — DHA                                 │
│ Sub: Solicitation W912DY-25-R-0042 · Due Aug 14, 2026                │
│ [Regenerate]  [Export]  [View History]                               │
├─────────────────────────────────────────────────────────────────────┤
│  EXECUTIVE SUMMARY                                                   │
│  3-sentence narrative with inline citations [1][2]                   │
├─────────────────────────────────────────────────────────────────────┤
│  KEY FINDINGS                                                        │
│  • Bullet with citation [3]                                          │
│  • Bullet with citation [1][4]                                       │
├─────────────────────────────────────────────────────────────────────┤
│  SUPPORTING EVIDENCE                                                 │
│  Cards: [Doc · page · section · snippet] x N                         │
├─────────────────────────────────────────────────────────────────────┤
│  RECOMMENDED ACTIONS                                                 │
│  Numbered actions, each with owner placeholder                       │
├─────────────────────────────────────────────────────────────────────┤
│  Footer: Generated by gpt-4.1-mini · 5.3s · 2026-06-09 14:22         │
│  by Alex Park · Prompt v1 · [View raw output]                        │
└─────────────────────────────────────────────────────────────────────┘
```

The Compliance Matrix and Risk Register replace the central body with a table; the executive summary header above them remains.

---

## 8. Empty / Insufficient-Context States

| Situation | Surface |
|-----------|---------|
| Module never run | `EmptyState` with "Generate {Module}" CTA, list of expected inputs |
| Documents still processing | `EmptyState` with status pills per doc, no CTA |
| LLM returned `insufficient_context` | Yellow banner: "We don't have enough source material to answer confidently." + list of `missing` items + "Upload {doc_type}" CTA |
| LLM error | Red banner with retry + audit link |

Never fabricate output. Never auto-retry on insufficient context.

---

## 9. Chat (AssistantPanel)

- Lives as a **right-side drawer**, not a page. Toggled from the top bar and from opportunity pages.
- Header: `Intelligence Assistant — {Opportunity name}`.
- Message bubbles: user (right, navy outline), assistant (left, white card).
- Every assistant message ends with a **Sources** strip showing citation chips.
- Empty state suggests analyst-style starter prompts:
  - "Summarize the major requirements."
  - "What are the key evaluation drivers?"
  - "Where are our biggest capability gaps?"
  - "What does SAM.gov tell us about this agency's buying patterns?"

---

## 10. Accessibility

- **WCAG 2.1 AA**. All status colors paired with text labels (not color alone).
- All interactive elements: keyboard-navigable; visible focus ring (`--miq-focus`).
- Color contrast: body text 7:1; secondary 4.5:1.
- All form fields have associated `<label>`.
- Tables: `<th scope>`, sortable columns expose `aria-sort`.
- Skip-to-content link in shell.
- Reduced motion: respect `prefers-reduced-motion`.

---

## 11. Responsive

- Designed first for **1440×900**. Supported down to **1024**.
- Below 1024: LeftNav collapses to a hamburger drawer; KPI rows stack 2×2 then 1×4.
- Below 768 (rare for the audience): tables become summary cards with "View full table" link.

---

## 12. Sample Tailwind Config (excerpt)

```ts
// tailwind.config.ts
import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy:    { 700: "#1B3957", 800: "#102A44", 900: "#0A1F33" },
        charcoal:{ 100:"#EEF1F4",300:"#C3C7CD",500:"#6B7079",700:"#3A3F45",900:"#1A1D21" },
        steel:   { 300: "#A5C0DE", 500: "#3F7AB8", 700: "#2A5A8C" },
        teal:    { 100: "#E1F1F2", 500: "#3FA2A6", 700: "#1E6F73" },
        status: {
          green:    "#2F7D55", greenBg:"#E6F2EB",
          amber:    "#B5780C", amberBg:"#FBF1DC",
          red:      "#A8302E", redBg:  "#F7E3E2",
        },
        canvas: "#F6F8FB",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(10,31,51,0.04), 0 1px 1px rgba(10,31,51,0.06)",
        elevated: "0 12px 32px rgba(10,31,51,0.12)",
      },
      borderRadius: { sm: "6px", md: "10px", lg: "14px" },
    },
  },
} satisfies Config;
```

---

## 13. Iconography

- **Lucide** icons (stroked, 1.5px). No filled solid icons. Brand-neutral.
- Module-group icons:
  - Capture: `target`
  - Operations: `activity`
  - Process: `git-branch`
  - Performance: `bar-chart-3`
  - Risk: `shield-alert`
  - Organizational: `users`
  - Market: `globe`
- Status icons paired with status colors only when reinforcing meaning (e.g. `circle-check`, `circle-alert`, `octagon-x`).
