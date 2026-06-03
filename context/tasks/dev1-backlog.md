# Dev 1 — Backlog (Architect + Senior)

> Owns: DB schema, credential encryption, multi-tenancy, **flow engine**, **flow builder**,
> auth scaffolding, handoff backend. Foundational work — most `[S]` items live here.
> Tags: `[S]` Shared (build first) · `[P]` Parallel · `[D]` Dependent.
> All tasks run full PIER (effort proportionate). **AI-junior?** = safe to delegate boilerplate to a sub-agent (Dev 1 reviews).
> Size: S ≈ ½ day · M ≈ 1 day · L ≈ 2 days.

## Legend per ticket
`ID · Title · [tag] · Size · Depends-on · AI-junior? · Context slice`
→ **Done when:** acceptance criteria.

---

## Epic A — Project skeleton  (T-S2)

**D1-01 · Init Django project + split settings · `[S]` · S · — · AI-junior: yes · architecture.md**
→ Done when: `config/` project with `base/dev/prod` settings, `.env` via `django-environ`; `manage.py runserver` boots reading `.env`.

**D1-02 · Create 6 apps + register · `[S]` · S · D1-01 · AI-junior: yes · architecture.md**
→ Done when: `apps/{tenants,flows,conversations,channels,handoff,audit}` exist, in `INSTALLED_APPS`, import clean.

**D1-03 · Wire Celery + Redis · `[S]` · M · D1-01 · AI-junior: yes · architecture.md C-02**
→ Done when: `config/celery.py` set up; a `ping` task runs on a worker and returns.

**D1-04 · Postgres connection · `[S]` · S · D1-01 · AI-junior: yes · architecture.md**
→ Done when: `DATABASES` from env; `manage.py migrate` runs clean against Postgres.

## Epic B — Data models + migrations  (T-S3, C-08)

**D1-05 · `tenants` model + admin register · `[S]` · M · D1-02 · AI-junior: partial · architecture.md §Data models**
→ Done when: all fields per spec; visible/editable in Django admin (config fields only).

**D1-06 · Token encryption at rest · `[S]` · L · D1-05 · AI-junior: NO (SEC-02) · CLAUDE.md §7**
→ Done when: `wa_access_token`/`ig_access_token` encrypted via Fernet; key from env, **not** in DB; tokens never appear in logs/repr. Resolves D-100.

**D1-07 · `flow_steps` + `flow_options` models · `[S]` · M · D1-02 · AI-junior: partial · architecture.md**
→ Done when: FKs correct; `button_label ≤ 20` enforced; DB constraint = exactly one `is_start=true` per tenant; null `next_step_id` = terminal.

**D1-08 · `sessions` + `messages` models · `[S]` · M · D1-02 · AI-junior: yes · architecture.md**
→ Done when: status enum (active|completed|handed_off); new session per conversation; messages link to session with direction.

**D1-09 · `audit_logs` + auto-record · `[S]` · M · D1-05 · AI-junior: NO (SEC-05) · CLAUDE.md §7**
→ Done when: model per spec; admin create/edit/delete recorded with actor + timestamp + JSON diff (FR-19).

**D1-10 · Migrations + constraints check · `[S]` · S · D1-05..09 · AI-junior: yes · —**
→ Done when: all migrations apply cleanly; single-start-step constraint verified by a test.

## Epic C — Auth scaffolding  (T-S4, C-06)

**D1-11 · Admin auth (single PO account) · `[S]` · M · D1-04 · AI-junior: NO (SEC-05) · AP-01**
→ Done when: login works; JWT or server session; no public registration; unauth API calls → 401.

**D1-12 · Example DRF endpoint (copy template) · `[S]` · M · D1-11 · AI-junior: yes · CLAUDE.md §6**
→ Done when: one resource has serializer + viewset + permission + test; documented as the pattern Dev 3 copies.

## Epic D — Flow engine  (T-P2, C-03)  ⚠️ stateless, all state in DB

**D1-13 · Session resolver · `[P]` · M · D1-08 · AI-junior: partial · FR-09, flow step 5**
→ Done when: get-or-create session per (tenant, channel, customer); new conversation → new session, no prior data referenced.

**D1-14 · Current-step renderer · `[P]` · M · D1-07,D1-13 · AI-junior: partial · FR-05/06**
→ Done when: given a session, returns greeting (first message) then step message + button options payload.

**D1-15 · Branching / advance · `[P]` · M · D1-14 · AI-junior: NO (core logic) · FR-07, flow step 7**
→ Done when: button reply matched to `flow_option`; session advances to `next_step_id`.

**D1-16 · Free-text handling · `[P]` · S · D1-14 · AI-junior: partial · FR-08, flow step 6**
→ Done when: free text resends current step + prompt; flow does not advance or break.

**D1-17 · Terminal handling · `[P]` · M · D1-15 · AI-junior: NO (core logic) · FR-10/12, flow step 8**
→ Done when: null `next_step_id` → if handoff enabled, emit handoff offer; else send closing, mark `completed`.

**D1-18 · Deleted-step recovery · `[P]` · S · D1-15 · AI-junior: yes · ERR-04**
→ Done when: `current_step_id` points to deleted step → reset to start, send greeting, log recovery event.

**D1-19 · Flow-engine unit tests · `[P]` · L · D1-13..18 · AI-junior: yes · FR-05..10**
→ Done when: tests cover greeting, branching, free-text, terminal, recovery paths; all green.

## Epic E — Flow builder  (T-D2, C-07, FR-17)  ⚠️ hardest UI

**D1-20 · Decide live-flow-edit behaviour · `[D]` · M · — · AI-junior: NO · D-103**
→ Done when: behaviour for active sessions on flow edit decided + documented in decisions.md (AP-04). Resolves D-103. **Blocks D1-21.**

**D1-21 · Step editor (form-based) · `[D]` · L · D1-20,D1-07 · AI-junior: partial · AP-02**
→ Done when: create/edit step (label + message_text), mark start step; form-based (no drag-drop).

**D1-22 · Option editor · `[D]` · M · D1-21 · AI-junior: partial · AP-02**
→ Done when: add/edit options (button_label + select next step from existing steps).

**D1-23 · Flow validation gate · `[D]` · L · D1-22 · AI-junior: NO (correctness) · AP-03**
→ Done when: before save/activate, validates exactly one start, all `next_step_id` valid, no orphans; invalid flows cannot be activated.

## Epic F — Handoff backend  (T-D3, C-05)

**D1-24 · Handoff trigger service · `[D]` · L · D1-17,D1-08 · AI-junior: partial · FR-11/13**
→ Done when: on "Talk to a human" → build payload (customer, channel, timestamp, path), send email (Dev 3 owns template), mark session `handed_off`, send customer confirmation, stop bot responses in session.

---

### Sequencing note
Epics **A→B→C are `[S]`** — Dev 1 does these first; they unblock Dev 2 and Dev 3.
Epic **D** can start once B is done (parallel with Dev 2/3 work).
Epics **E, F** are `[D]` — last, and E is gated on resolving **D-103**.
