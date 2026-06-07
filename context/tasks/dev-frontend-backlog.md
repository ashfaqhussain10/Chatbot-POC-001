# Frontend — Backlog (React SPA · "Relay")  ·  Owner: Dev 3 (React) + Dev 1 (builder logic)

> The custom admin panel (D-107). React SPA against the Django/DRF API, JWT auth.
> Spec: [`../frontend_spec.md`](../frontend_spec.md). Live phone preview = **Phase 2**.
> Tags: `[S]` Shared (scaffold first) · `[P]` Parallel · `[D]` Dependent.
> **Cross-track gate:** each screen is blocked until its **DRF endpoint** exists (see the
> backend Admin-API tasks). Size: S ≈ ½d · M ≈ 1d · L ≈ 2d.

`ID · Title · [tag] · Size · Depends-on · AI-junior? · Refs` → **Done when:** criteria.

---

## Epic FE-A — Scaffold & foundation `[S]` (build first)

**F-01 · React app scaffold · `[S]` · M · — · AI: yes · frontend_spec.md §2**
→ Done when: Vite + React + TypeScript app builds; routing in place; design tokens (§2) wired as CSS vars / theme; Plus Jakarta Sans + JetBrains Mono loaded.

**F-02 · API client + auth handling · `[S]` · M · F-01 · AI: partial · architecture.md §6.1**
→ Done when: fetch/axios wrapper sends `Authorization: Bearer <jwt>`; stores/clears token; on 401 → redirect to login; base URL from env.

**F-03 · App shell · `[S]` · M · F-01 · AI: yes · frontend_spec.md §3**
→ Done when: top bar (logo, breadcrumb, account), left sidebar (Dashboard, Clients + count), scrollable main, protected-route wrapper.

**F-04 · UI primitives · `[S]` · L · F-01 · AI: yes · frontend_spec.md §2/§10**
→ Done when: reusable Button, Card, Badge, Table, Modal, Toast, Input, Textarea, Toggle, Skeleton, EmptyState components match the tokens.

## Epic FE-B — Auth & dashboard `[P]`

**F-05 · Login screen · `[P]` · M · F-02,F-04 · AI: yes · FR-01**
→ Done when: centred card, email+password, submit; error (red borders + message), loading (spinner), success → Dashboard, JWT persisted.

**F-06 · Dashboard · `[P]` · L · F-03,F-04 · AI: partial · frontend_spec.md §5**
→ Done when: 4 stat tiles, "how it works" card, client-card grid (clickable → detail), empty state.

## Epic FE-C — Clients & config `[P]`

**F-07 · Clients list · `[P]` · M · F-04 · AI: yes · FR-15**
→ Done when: table (business/WA/IG/handoff/flow/status), row click → detail, empty state, "New client" button.

**F-08 · Create client modal · `[P]` · M · F-07 · AI: yes · FR-16**
→ Done when: fields + validation (name ≥2 → enables Create); on create → toast + navigate to detail (Flow builder); dismiss on scrim/Cancel.

**F-09 · Client detail shell + tabs · `[P]` · M · F-03 · AI: yes · frontend_spec.md §3**
→ Done when: header (emoji, name, status, back arrow), 3 tabs (Settings/Flow builder/Conversations), defaults to Flow builder.

**F-10 · Settings tab · `[P]` · L · F-09,F-04 · AI: partial · FR-05/11/12**
→ Done when: greeting/closing inputs, handoff toggle revealing email (+ warning when on w/o email), channels & identity; saves to API.

## Epic FE-D — Flow builder `[D]` (hardest — Dev 1 pairs)

**F-11 · Step list (collapsed) · `[D]` · L · F-09 · AI: partial · FR-17 / frontend_spec.md §8a**
→ Done when: step cards with mono ID, label, START/END badge, option-count chip, option map; "Add step" ghost button.

**F-12 · Step editor (expanded) · `[D]` · L · F-11 · AI: NO (core UX) · frontend_spec.md §8b**
→ Done when: name, message (char count), start toggle (single-start logic), option rows (label 20/20 + target select + delete), add option, delete step.

**F-13 · Live validation + activation · `[D]` · L · F-12 · AI: NO (correctness) · frontend_spec.md §8d**
→ Done when: V-01..V-06 run on every change; banner (valid / N issues + list); Activate disabled when invalid; Deactivate always allowed. Server remains source of truth.

## Epic FE-E — Conversations `[P]/[D]`

**F-14 · Conversation list · `[P]` · M · F-09 · AI: yes · FR-18**
→ Done when: session rows (channel badge, customer id, path trail, timestamp, status), newest-first, empty state.

**F-15 · Message thread expand · `[D]` · M · F-14 · AI: yes · frontend_spec.md §9**
→ Done when: row expands inline thread (bot left, customer right, system events centred); closes on re-click.

## Epic FE-F — Integration & polish `[D]`

**F-16 · Global states · `[P]` · M · F-04 · AI: yes · frontend_spec.md §10**
→ Done when: toasts, loading skeletons, empty states applied consistently.

**F-17 · Wire all screens to live API · `[D]` · L · all above · AI: partial · §12**
→ Done when: every screen reads/writes real endpoints; error + loading handled; no mock data.

## Phase 2 (deferred)

**F-P1 · Live phone preview / simulator · `[phase2]` · XL · F-13 · AI: NO · frontend_spec.md §11**
→ Done when: in-browser WhatsApp/IG simulator runs a client's real flow (branch/re-prompt/handoff) with channel toggle + reset.

---

### Hard dependency on the backend
The SPA renders nothing real until the **Admin API endpoints** exist (auth, tenant CRUD,
config, flow CRUD, sessions/messages read). Backend API work must lead frontend by a step.
The former "Dev 3 admin CRUD" tickets become **DRF endpoints** feeding these screens.
