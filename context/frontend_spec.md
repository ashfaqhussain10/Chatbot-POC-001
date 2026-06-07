# Frontend Spec — "Relay" Admin Panel

> **Owner:** Dev 1 (with Dev 3). The product UI spec. Source design: `Frontend Handoff.html`
> + screenshots in [`../design_screenshots/`](../design_screenshots/) + interactive
> prototype `Frontend Handoff - Relay Admin Panel.html`. Pairs with [`prd.md`](prd.md)
> (the *what*), [`architecture.md`](architecture.md) §6.1 (how it's wired).

---

## 1. Purpose & scope

The **only custom UI we build is the admin panel** — the product owner's console for
managing tenants and their flows. Customers interact through WhatsApp/Instagram's own
apps; there is **no chat UI to build**.

- **Stack:** custom **React SPA** against the Django **DRF API**, JWT auth (D-107).
- **In scope (v1):** Login, Dashboard, Clients list + create, Client detail (Settings /
  Flow builder / Conversations).
- **Phase 2 (deferred):** the **live phone preview/simulator** (see §11).
- **Out of scope:** any chat UI, WhatsApp/Instagram client rendering, customer onboarding,
  agent inbox.

---

## 2. Design system (tokens)

Brand: **Relay** — clean, blue-accented, card-based, generous whitespace.

| Token | Value | Use |
|-------|-------|-----|
| `--accent` | `oklch(0.52 0.13 256)` (~`#3a5fd9`) | Primary buttons, active nav, badges, focus rings |
| `--accent-weak` | `oklch(0.95 0.025 256)` | Active nav bg, badge backgrounds |
| `--bg` | `#f4f5f7` | Page background, alt table rows |
| `--surface` | `#ffffff` | Cards, sidebar, modal |
| `--border` | `#e6e8ed` | Borders, dividers |
| `--ink` / `--ink2` / `--ink3` | `#1b1f26` / `#52596a` / `#8b93a1` | Primary / secondary / muted text |
| `--ok` | `oklch(0.42 0.10 155)` | Active / Live / Completed (green) |
| `--warn` | `oklch(0.50 0.12 70)` | Handoff / warning (amber) |
| `--danger` | `oklch(0.46 0.14 25)` | Validation errors, delete |
| Font — UI | **Plus Jakarta Sans** (400/600/700/800) | Everything |
| Font — mono | **JetBrains Mono** | Step IDs, phone numbers, code |
| Radius | `7px` / `11px` / `16px` | Buttons / cards+inputs / modals |

---

## 3. App shell & navigation

Persistent after login (see `design_screenshots/02-dashboard.png`):
- **Top bar:** Relay logo + breadcrumb (e.g. `Clients › Verde Kitchen`) · "Prototype"
  pill · account email + avatar.
- **Left sidebar (~218px):** Dashboard, Clients (with live/total count badge).
- **Main area:** scrollable content.

**Navigation map:**
```
Login ──► Dashboard ──► Clients list ──► Client detail
                                            ├─ Settings      (FR-05/11/12)
                                            ├─ Flow builder  (FR-17)
                                            └─ Conversations (FR-18)
   Clients list ──(New client)──► Create modal ──► Client detail (Flow builder tab)
```
Rules: session persists until explicit sign-out; clicking a client (card or row) opens
detail defaulting to the **Flow builder** tab; back arrow (←) in the client header returns
to the list.

---

## 4. Screen 1 — Login  ·  FR-01
*(`design_screenshots/01-login.png`)*

- Full-viewport centred card (~360px) on `--bg`; Relay logo + wordmark above.
- Fields: **Email**, **Password** (both required). Submit on Enter or button.
- Below card: muted note "Secure session · HTTPS only · no public registration".
- **States:** error → red borders + inline message, button re-enables (no lockout v1);
  loading → button spinner, disabled; success → redirect to Dashboard, JWT persisted.

---

## 5. Screen 2 — Dashboard
*(`design_screenshots/02-dashboard.png`)*

- Title + one-line product explainer.
- **"How it works"** card: 3 steps (1 Configure · 2 Customer chats · 3 End or hand off).
- **4 stat tiles:** Clients (active/total) · Conversations (started today) · Human handoffs
  (emails sent) · Channels (WA · IG counts).
- **"Your clients"** card grid: each card = emoji, name, phone, Live/Off badge, step count,
  chat count, handoff on/off. Whole card clickable → Client detail (Flow builder tab).
- **Empty state:** centred "No clients yet" + CTA → Create modal.

---

## 6. Screen 3 — Clients list (+ Create modal)  ·  FR-15 / FR-16
*(`design_screenshots/03-clients-list.png`)*

**List:** table — Business (emoji+name) · WhatsApp · Instagram · Handoff (Email/Off) ·
Flow (N steps chip) · Status (Live/Inactive) · chevron. Row click → Client detail.
"**+ New client**" button (top-right) → Create modal. Empty state with CTA.

**Create client modal** (FR-16):
- Fields: **Business name** (required, ≥2 chars — Create disabled until met),
  WhatsApp number (optional, E.164 on save), Instagram (`@handle`), Handoff email
  (optional; if provided, `handoff_enabled` defaults true).
- **On create:** tenant created `is_active=false`; starter flow injected (1 step, 2
  placeholder buttons); greeting/closing auto-filled from name; modal closes → Client
  detail (Flow builder tab); toast "Client created".
- **Dismiss:** scrim or Cancel closes without saving (nothing committed).

---

## 7. Screen 4 — Client detail · Settings tab  ·  FR-05 / FR-11 / FR-12
*(`design_screenshots/04-screens.png`)*

Three sections:
- **Messages:** Greeting (FR-05 — sent first, before options) · Closing (FR-12 — sent only
  when flow ends *and* handoff off; if handoff on, show muted note "Only sent when handoff
  is off").
- **Human handoff:** toggle "Offer 'Talk to a human' at flow end" (FR-11). On → reveals
  Handoff email input; on without email → inline warning "Add a handoff email to enable
  this".
- **Channels & identity:** business name, WhatsApp number, Instagram. Status badge
  (Active/Inactive) read-only here — controlled by Activate in Flow builder.

Save model: auto-save on blur **or** explicit Save — pick one and be consistent.

---

## 8. Screen 5 — Flow builder  ·  FR-17  (most important)
*(`design_screenshots/03-05-flow-builder.png`)*

The core authoring surface. A list of **step cards**; one expands to edit at a time.

**Validation banner (top):** green "Flow valid" + plain confirmation when all checks pass;
red "N issues" + error list when not. **Activate/Deactivate** button at right — *disabled
when the flow is invalid and inactive*.

**8a. Collapsed step card:** mono step ID (e.g. `v_start`), label, START/END badge,
option-count chip, and the **option map** — each row `[Button label] › [Target step]` or
*"End flow"* (italic). Header click → expand. Ghost "**Add step**" button below the list.

**8b. Expanded / edit mode:**
- **Step name** (internal label, not shown to customers).
- **Message text** (sent to customer; emoji ok; show char count over 800, WA rec ≤1024).
- **Start-step toggle** — exactly one start; turning one ON turns the previous OFF;
  turning the only start OFF → immediate validation error.
- **Option rows:** `[Label input 20/20] › [Target step select] [🗑]`. Label hard-capped at
  20 chars (counter; turns red at limit); target dropdown = all other steps + "⏹ End flow".
  "Add option" appends a row.
- **>3 options:** inline warn "4+ options → sent as a list message" (allowed, flagged).
- **Delete step:** red button; incoming links to it reset to "End flow"; validation re-runs.

**8c. Interactions (live):** every edit applies immediately (live save) and **re-runs
validation** — no explicit Validate button, no unsaved-changes warning. Activate (valid) →
`is_active=true`, badge → Live, button → Deactivate. Activate (invalid) → disabled.
Deactivate → always allowed.

**8d. Validation rules (block activation unless noted):**

| ID | Name | Triggers when |
|----|------|---------------|
| V-01 | No start step | Zero steps have `is_start=true` |
| V-02 | Multiple start steps | >1 step `is_start=true` (guard even though toggle prevents it) |
| V-03 | Broken link | An option's target step no longer exists |
| V-04 | Unreachable step | A step can't be reached from start (saves; can't activate) |
| V-05 (soft) | Label too long | >20 chars (input capped; warn only) |
| V-06 (soft) | Too many buttons | >3 options → list message (warn, don't block) |

> These map to the backend flow-validation gate (D1-23 / AP-03). The frontend mirrors them
> for instant feedback; the **server is the source of truth** on activation.

---

## 9. Screen 6 — Conversations  ·  FR-18
*(`design_screenshots/05-screens.png`)*

Per-client read-only log. Each row = one session: channel badge (WA green / IG purple) ·
customer id (phone or `@handle`) · **path trail** (button labels joined by ›) · timestamp ·
status badge. Newest first.
- **Expand row** → inline message thread: bot left, customer right, system events (e.g.
  "📧 Handoff email sent") centred in a pill. Re-click to close.
- **Status:** Completed (green) · Handed off (amber) · Active (blue).
- **Empty state:** "No conversations logged yet — run the flow to see logs here." No
  search/filter in v1.

---

## 10. Global states & patterns

- **Toasts:** bottom-centre, dark pill + check, auto-dismiss ~2.6s ("Client created", etc.).
- **Loading:** button spinner (disable button); skeleton rows for lists; no full-page
  spinners except the initial auth check.
- **Empty states:** every list/table has a centred icon + one-line label + CTA where apt.
- **Inline validation (flow builder):** runs on every change; red card above the list + red
  badge in the banner; clears automatically when resolved.

---

## 11. Phase 2 — Live phone preview / simulator (deferred)

On the right of Flow builder & Settings, a **phone frame** simulates WhatsApp/Instagram and
**runs the client's real flow** in-browser: tap buttons to branch, type free text to see
the re-prompt, reach the end to see handoff. A channel toggle (WhatsApp/Instagram) and a
reset. **Not built in v1** — valuable as a built-in tester, but the largest single piece of
frontend work. Build the functional admin screens first (D-107).

---

## 12. Screen → tickets / API mapping

| Screen | FR | Backend it needs |
|--------|----|------------------|
| Login | FR-01 | Auth endpoint + JWT (D1-11) |
| Dashboard | — | Stats (derive from tenants/sessions) |
| Clients list + create | FR-15/16 | Tenant CRUD API (C-06) on the tenants model (D1-05) |
| Settings | FR-05/11/12 | Tenant config endpoints |
| Flow builder | FR-17 | Flow step/option CRUD + validation (D1-21..23) |
| Conversations | FR-18 | Read sessions + messages (D1-08) |

**Note:** every screen now needs **REST endpoints + serializers** on the Admin API (C-06) —
this is the work that grew when we chose a SPA over Django admin (D-107). A dedicated
**frontend ticket set** (React app scaffold, auth, each screen) still needs adding to the
backlog.

---

## 13. Asset references

- Written design: `Frontend Handoff.html`
- Interactive prototype: `Frontend Handoff - Relay Admin Panel.html` (needs a browser)
- Screenshots: [`../design_screenshots/`](../design_screenshots/) — `01-login`,
  `02-dashboard`, `03-clients-list`, `04-screens` (settings), `03-05-flow-builder`,
  `05-screens` (conversations).
