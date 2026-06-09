# context/decisions.md — Decision Log

> Owner: Senior. ADR-style. Append new decisions at the top. Never rewrite history —
> supersede instead. Update the relevant status when a decision is resolved.

## Format
```
## D-NNN — <title>   [OPEN | DECIDED | SUPERSEDED]
Date: YYYY-MM-DD · Owner: <who>
Context: <why this needs deciding>
Decision: <what we chose> (blank while OPEN)
Consequences: <what it affects>
```

---

## D-109 — Frontend in a separate repository   [DECIDED]
Date: 2026-06-09 · Owner: PO + Dev 1
Context: D-107 assumed a monorepo (Django backend at root + a `frontend/` folder). The PO
wants a clean separation of concerns — the frontend in its own repo, not inside this one.
Decision: The React SPA lives in a **separate git repository / folder**, independent of
this backend repo. The two communicate only over the DRF API (JWT + CORS). This backend
repo contains **no `frontend/` folder**. Build order: **finish the backend first, then the
frontend.**
Consequences:
- Supersedes the "`frontend/` folder / monorepo" part of D-107, architecture §6.1, CLAUDE §6.
- Backend must enable **CORS** for the SPA origin (`django-cors-headers`) when FE work starts.
- Fully independent CI/CD + deploys (already so: Railway backend, Cloudflare/Vercel SPA).
- `context/tasks/dev-frontend-backlog.md` stays here as planning reference; it (and
  `frontend_spec.md`) can be copied into the frontend repo when it's created.

## D-108 — Deployment & infrastructure (≈$5/mo app host, rest free)   [DECIDED]
Date: 2026-06-08 · Owner: Dev 1 + PO
Context: Need a production-reliable backend for ≤15 tenants in ~2 months, mostly free tier.
Webhooks require an **always-on** host (free hosts sleep → dropped webhooks). Celery's
Redis polling busts free Redis command quotas; an always-on backend would also bust Neon's
free **compute-hour** budget.
Decision:
- **App + worker host: Railway** (~$5/mo) — one always-on deploy running web (gunicorn) +
  the queue worker. No sleep → webhooks never missed (NFR-02).
- **Database: Supabase** (free, **always-on** Postgres) — chosen over Neon, whose free
  tier meters compute hours and would be exceeded by a 24/7 backend.
- **Queue: django-q2** (database-backed) — replaces Celery + Redis. Fewer services, fully
  free, ample at this scale. **Supersedes the Celery+Redis part of D-001.**
- **Frontend host: Cloudflare Pages / Vercel** (free, always-on CDN) for the React SPA.
- **Email: Resend / Brevo** (free tier) for handoff.
Consequences:
- Total cost ≈ $5/mo; everything except the app host is free.
- Remove Celery/Redis wiring (`config/celery.py`, `CELERY_*` settings, deps); add django-q2.
- Row locking (D-105) still works — Supabase is Postgres.
- Secrets (D-106) sourced from Railway environment variables.
- `requirements.txt`, settings, and the queue task code change accordingly (next slice).

## D-107 — Frontend = custom React SPA (supersedes Django-admin plan)   [DECIDED]
Date: 2026-06-08 · Owner: Dev 1 + PO
Context: The "Relay" frontend handoff designs a fully custom, branded admin console
(login, dashboard, clients, client detail with Settings / Flow builder / Conversations
tabs, plus a live phone preview). Django's built-in admin cannot render this. Earlier
guidance (D-001 / architecture §5) assumed Django admin for CRUD/config/logs + a custom
flow builder only.
Decision: Build a **custom React SPA** against the **Django + DRF admin API** (C-06),
with **JWT (token) auth** and CORS. Django admin is **retained for internal dev/debug
only**, not the product UI. Team is comfortable with React (low risk). The **live phone
preview/simulator is Phase 2** — build the functional admin screens first.
Consequences:
- Supersedes the "Django admin for FR-15/16/18" portion of D-001 and architecture §5.
- **Elevates the Admin API (C-06):** every screen needs REST endpoints + serializers.
- Adds a frontend stack: separate React app, CORS config, JWT auth, its own build/deploy.
- Dev 3's scope shifts from "Django admin config screens" to React frontend; the flow
  builder UI (D1-21..23) becomes React, fed by flow-config endpoints.
- Timeline: ~3–4 weeks added vs the Django-admin plan.
- The `admin.py` registrations already built remain useful for internal data inspection.
- New frontend ticket set required (to be added to the backlog).

## D-106 — Secrets management in production   [DECIDED]
Date: 2026-06-04 · Owner: Dev 1
Context: `.env` files are fine for local dev but are not a production secret store. The
encryption key (SEC-02) and tenant Meta tokens must be protected in prod.
Decision: Dev uses `.env`. **Production** sources the encryption key and other secrets
from a managed secrets store (cloud KMS / Secrets Manager / Vault), injected as env vars
at runtime — never committed, never stored in the DB. Settings read from env regardless
of source, so no code differs between dev and prod. The specific provider is chosen at
deploy time (deferred sub-decision).
Consequences: Affects D1-06 and deployment. No code change dev↔prod.

## D-105 — Session concurrency control   [DECIDED]
Date: 2026-06-04 · Owner: Dev 1
Context: Two inbound messages for the same session can arrive near-simultaneously and
race on `current_step_id`, double-advancing or corrupting flow state.
Decision: All session-state reads/writes during flow execution run inside a DB
transaction using `select_for_update()` to lock the session row, so concurrent events
for the same session serialize.
Consequences: Flow engine (D1-13..17) wraps step-resolution + advance in an atomic,
row-locked transaction. Requires a DB with real row locking — **Postgres** in any shared
environment (SQLite is dev-only).

## D-104 — Webhook idempotency / dedup   [DECIDED]
Date: 2026-06-04 · Owner: Dev 2
Context: Meta retries webhooks; duplicate delivery of the same message is expected.
Without dedup, a customer could be advanced through the flow twice for one tap.
Decision: Persist the provider message id on each inbound message and enforce uniqueness
per (tenant, channel, provider_message_id). On receipt of an already-seen id, ack 200 and
skip processing (idempotent).
Consequences: `messages` gains `provider_message_id` + a unique constraint; the webhook
worker checks before processing. Affects channels (D2-05..08) + conversations (D1-08).

## D-103 — Live flow-change behaviour (T-03)   [OPEN]
Date: 2026-06-03 · Owner: Dev 1
Context: When the product owner edits a live flow, how are **active sessions** handled?
Changes must take effect on **new** sessions (AP-04). Active-session behaviour must be
decided and documented **before the flow builder is built**.
Decision: —
Consequences: Blocks flow builder (FR-17). Affects flow engine session handling.

## D-102 — Instagram interactive message types (T-02)   [DECIDED]
Date: 2026-06-09 · Owner: Dev 2
Context: Must decide Instagram DM button/quick-reply support before the IG renderer.
Decision: **Instagram via Meta's Graph API (Instagram Messaging) directly** — same Meta
ecosystem as WhatsApp (D-101). Use native quick-replies / generic-template buttons where
available; **fallback = numbered text menu** (`1`/`2`/`3`), Instagram-only (IG-02). Exact
button capability confirmed during channel build; PO approves the fallback UX.
Consequences: Unblocks the IG renderer (D2-15..18). IG logic must not affect WhatsApp.

## D-101 — WhatsApp connection = Meta Cloud API (direct)   [DECIDED]
Date: 2026-06-09 · Owner: PO + Dev 2
Context: How to connect WhatsApp — Meta Cloud API directly vs a third-party BSP
(360dialog/Twilio/Gupshup).
Decision: **Meta WhatsApp Cloud API directly — no third-party BSP.** Rationale: fits the
free-tier goal (no per-number BSP fees; only per-conversation messaging with a free
allowance), lets us **build + test now on Meta's free test number**, and keeps lock-in low
(our message sender C-04 is provider-agnostic). Onboarding **real** client numbers later
uses Meta **Embedded Signup** + Business Verification (an ops track, doesn't block code).
Consequences: Unblocks webhook receiver (C-01) + message sender (C-04). One app-level
webhook receives all tenants' events, routed by `phone_number_id`. Per-tenant tokens stay
encrypted (D-100).

## D-100 — Credential encryption approach (T-04)   [DECIDED]
Date: 2026-06-08 · Owner: Dev 1
Context: Which encryption mechanism + key-management strategy for Meta access tokens.
Tokens encrypted at rest; key must **not** live in the DB (SEC-02).
Decision: **Fernet** (`cryptography`) via a custom `EncryptedTextField`
([apps/tenants/fields.py](../apps/tenants/fields.py)) — authenticated symmetric
encryption, encrypt-on-write / decrypt-on-read. Key from `settings.FERNET_KEY` (env /
Railway secret in prod; dev-only default in dev settings) — never stored in the DB (D-106).
Consequences: Implemented in D1-06 (tenants `wa_access_token` / `ig_access_token`).
Forward-compatible with key rotation (versioned key) if needed later.

---

## D-001 — Backend stack = Django + DRF   [DECIDED]
Date: 2026-06-03 · Owner: Team
Context: PRD left stack to the team (Node vs Python recommended).
Decision: **Django + DRF**, Celery + Redis, PostgreSQL. Django admin covers admin CRUD/
config/log views cheaply; custom views only for the flow builder.
Consequences: Sets repo layout and conventions (see CLAUDE.md §6, architecture.md).
