# Technical Architecture Document

> **Owner:** Architect (Dev 1). The *how* — the authoritative description of how the
> system is built. Keep in sync with code. Pairs with [`prd.md`](prd.md) (the *what*),
> [`security.md`](security.md) (access & security), and [`decisions.md`](decisions.md)
> (the rationale log).

---

## 1. Purpose & scope

This document describes the architecture of the **multi-tenant, rule-based chatbot
platform** that is the first point of contact for customers messaging a business on
**WhatsApp or Instagram**. Conversation flows are **button-driven** (no NLP). A single
product owner configures everything; business clients have no login. v1 targets
**1–10 tenants**, with a design that does not block scaling to 50+.

In scope: backend services, data model, integrations, deployment, and the operational
properties (resilience, scalability, observability). Out of scope: the frontend spec
(separate document) and the product requirements (see `prd.md`).

---

## 2. Architectural principles

1. **Monolith with clean internal module boundaries.** For 1–10 tenants, microservices
   are pure cost. Build one Django project with well-separated apps that *could* be
   extracted later — but do not extract now.
2. **Stateless compute, stateful database.** The flow engine holds no in-memory session
   state; everything is read from and written to Postgres. This is what makes the web
   and worker tiers horizontally scalable.
3. **Async by default at the edge.** The webhook endpoint does the minimum (verify,
   enqueue, ack) and returns fast; all real work happens in a background worker.
4. **Tenancy is a first-class column.** Every domain row is FK-scoped to a tenant; every
   query filters by it. Isolation is enforced by data design, not convention.
5. **Security is non-negotiable and not delegated.** See `security.md`. The guardrails
   (SEC-01..05) are invariants, not features.
6. **Config over code for environments.** The same artifact runs in dev and prod; only
   environment variables differ (12-factor).

---

## 3. System context

How the platform sits between Meta, the product owner, and its infrastructure.

```
        ┌──────────────┐      messages       ┌───────────────┐
        │ End customer │ <─────────────────> │  Meta (WA/IG) │
        └──────────────┘                     └───────┬───────┘
                                                     │  inbound webhooks (HTTPS, signed)
                                                     │  outbound Send API calls
                                                     ▼
   ┌──────────────────────────────────────────────────────────────┐
   │                 Chatbot Platform  (this system)                │
   │     web (Django/DRF)  ·  worker (Celery)  ·  admin (Django)    │
   └─────────┬──────────────────┬───────────────────┬──────────────┘
             │                  │                   │
             ▼                  ▼                   ▼
       ┌───────────┐      ┌───────────┐      ┌──────────────┐
       │ PostgreSQL│      │   Redis   │      │ Email (SES / │
       │  (state)  │      │  (broker) │      │  SendGrid)   │
       └───────────┘      └───────────┘      └──────────────┘
             ▲
             │ HTTPS (admin panel)
       ┌─────┴───────┐
       │ Product     │   configures tenants, flows, views logs
       │ owner       │
       └─────────────┘
```

**External actors & systems:**
- **End customer** — never touches the platform directly; only messages the business via Meta.
- **Meta (WhatsApp via BSP, Instagram)** — delivers inbound webhooks and accepts outbound sends.
- **Product owner** — the only human user of the platform; uses the admin panel over HTTPS.
- **Email provider (SES/SendGrid)** — delivers handoff emails to business staff.

---

## 4. Logical component architecture

One Django project, six apps, mapped to the PRD's components (C-01..C-08).

```
                         ┌───────────────────────────────────────────┐
   inbound webhook  ───► │ channels: webhook receiver (C-01)          │
                         │   verify signature → route tenant → enqueue│
                         └───────────────┬───────────────────────────┘
                                         │ Celery task (C-02)
                                         ▼
                         ┌───────────────────────────────────────────┐
                         │ flows: flow engine (C-03)  [stateless]     │
                         │   resolve session → decide next step       │
                         └───────┬───────────────────────┬───────────┘
                                 │ outbound              │ terminal + handoff
                                 ▼                       ▼
                  ┌──────────────────────────┐  ┌──────────────────────┐
                  │ channels: sender (C-04)   │  │ handoff service (C-05)│
                  │  per-tenant Meta API +    │  │  email + mark + stop  │
                  │  WhatsApp 24h window      │  └──────────────────────┘
                  └──────────────────────────┘
   ┌─────────────────────────────────────────────────────────────────┐
   │ tenants + DRF: admin API (C-06)  ·  Django admin panel (C-07)     │
   │ audit: audit log    ·    conversations: sessions + messages       │
   │ all → PostgreSQL (C-08)                                           │
   └─────────────────────────────────────────────────────────────────┘
```

| Django app | Component | Responsibility | Owner |
|------------|-----------|----------------|-------|
| `channels` | C-01 Webhook receiver | Public HTTPS endpoint; validate signature; identify tenant; queue event. Respond 200 < 5s. | Dev 2 |
| `channels` | C-02 Queue | django-q2 (DB-backed) decouples receipt from execution; retries + failed-task record. | Dev 2 |
| `flows` | C-03 Flow engine | Load tenant flow; determine current step; return next message + buttons. **Stateless** — all state in DB. | Dev 1 |
| `channels` | C-04 Message sender | Send via correct Meta API per tenant; enforce WhatsApp 24h window. | Dev 2 |
| `handoff` | C-05 Handoff service | On request: send email, mark session handed off, stop bot. | Dev 1 (backend) / Dev 3 (email content) |
| `tenants` + DRF | C-06 Admin API | Tenant CRUD, flow config, toggles, logs. Auth-protected. | Dev 1 (scaffold) / Dev 3 (endpoints) |
| React SPA | C-07 Admin panel | Custom web UI for product owner (Relay design). Flow builder = hardest piece. | Dev 3 (screens) / Dev 1 (builder logic) |
| `audit` | (FR-19) | Append-only record of admin actions. | Dev 1 |
| all apps | C-08 Database | Tenants, flows, sessions, logs, audit. | Dev 1 |

---

## 5. Technology stack & rationale

| Concern | Choice | Why this, not the alternative |
|---------|--------|-------------------------------|
| Web/backend | **Django + DRF** | Batteries-included: ORM, migrations, and a free admin that covers most of the admin panel. DRF for the webhook + admin API. Chosen over Flask/FastAPI because the admin alone saves weeks for FR-15/16/18. |
| Async/queue | **django-q2** (DB-backed) (D-108) | Database is the broker — no Redis. Fewer services, fully free, ample for ≤15 tenants. Supersedes Celery+Redis. |
| Database | **PostgreSQL — Supabase** (D-108) | Relational flow data; partial unique indexes + row locking (`select_for_update`). Supabase free is **always-on** (Neon's free tier meters compute hours → exceeded by a 24/7 backend). |
| Frontend | **Custom React SPA** (D-107) | The "Relay" design is fully custom; built as a single-page app against the DRF API. JWT auth + CORS. |
| Admin UI (internal) | **Django admin** — dev/debug only | Retained for internal data inspection, **not** the product UI (superseded by the SPA, D-107). |
| Email | Django email → **Resend / Brevo** (D-108) | Transactional deliverability; free tier ample for handoff volume. |
| Hosting | **Railway** (app + worker), **Supabase** (DB), **Cloudflare Pages/Vercel** (SPA) (D-108) | One always-on Railway deploy runs gunicorn + the django-q2 worker — no sleep, so webhooks are never missed. ≈$5/mo; rest free. |

---

## 6. Deployment / runtime architecture

For v1 a **single always-on Railway deployment** runs both the web server and the queue
worker. The pieces stay logically separate so they can scale apart later (§13), but they
co-locate now to stay near-free and always-on (D-108).

```
                          Internet (HTTPS)
                                │
          ┌─────────────────────┴──────────────────────┐
          ▼                                             ▼
  React SPA                                  Railway deployment (always-on, ~$5/mo)
  (Cloudflare Pages / Vercel)                ┌────────────────────────────────────┐
   static; JWT in calls  ───────────────────► gunicorn (web): /webhook + admin API │
                                             │ django-q2 worker: engine/send/handoff│
                                             └───────┬────────────────────┬────────┘
                                                     ▼                    ▼
                                                 Supabase            Resend / Brevo
                                                 (Postgres,           (handoff email)
                                                  always-on; also
                                                  the django-q2 broker)
```

- **Web** (`gunicorn config.wsgi`) — serves the webhook + admin API. Stateless.
- **Worker** (`python manage.py qcluster`) — consumes queued tasks (**broker = the DB**),
  runs the flow engine, sends messages, triggers handoff. Stateless.
- Both run in the **one Railway deployment** (via a process manager) — **no sleep**, so
  inbound webhooks are answered within Meta's 5s window (NFR-01/02). A sleeping host would
  cold-start and miss webhooks → lost messages.
- **Supabase** — single source of truth *and* the django-q2 broker (no Redis).

For local dev this collapses: SQLite fallback for the DB and the django-q2 worker run
locally (or sync mode) — no external services needed.

### 6.1 Frontend architecture (React SPA — D-107)

The product UI is a **custom React single-page app** (the "Relay" design), served as
static assets, talking to the Django **DRF API** (C-06). Full UI behaviour lives in
[`frontend_spec.md`](frontend_spec.md); the architectural shape:

```
   Browser ──► React SPA (static: CDN / static host)
                  │  JSON over HTTPS, JWT in Authorization header
                  ▼
            Django + DRF API  (/api/...)
                  │
            Postgres / Redis / email   (as in §6)
```

- **Build/deploy:** the SPA is a **separate repository** (D-109), built and deployed to a
  static host/CDN independently of this backend; the Django API deploys as in §6.
- **Auth:** JWT. The SPA stores the token and sends it as `Authorization: Bearer …`;
  every admin endpoint enforces it (401 if absent — SEC-05).
- **CORS:** the API allows the SPA's origin only (locked down in prod).
- **Django admin** still runs at `/admin/` for internal data inspection — not the product UI.
- **Phase 2:** the live phone preview/simulator (runs a client's real flow in-browser) is
  deferred; build the functional admin screens first.

---

## 7. External integrations

| Integration | Direction | Auth | Key constraints |
|-------------|-----------|------|-----------------|
| **WhatsApp Cloud API** (Meta direct, D-101) | inbound webhook + outbound send | Per-tenant access token (encrypted at rest); Meta **app secret** for HMAC | **24h window** (WA-03): interactive messages only within 24h of last customer message. Buttons ≤ 3, list ≤ 10, labels ≤ 20 chars (WA-02). GET verification handshake (WA-04). One webhook for all tenants, routed by `phone_number_id`. |
| **Instagram Messaging** (Meta Graph API direct, D-102) | inbound webhook + outbound send | Per-tenant token; `instagram_manage_messages` + `pages_messaging` via Meta OAuth (IG-03); linked FB Page | Quick-replies/template buttons where available; fallback = numbered text menu `1/2/3` (IG-02), Instagram-only. |
| **Email (Resend / Brevo)** | outbound | API key (env / Railway secret) | Transactional only; handoff notifications (FR-11). Free tier ample. |

**Provider note:** we use Meta directly (no BSP). The message sender (C-04) still isolates
the send call behind a per-channel implementation, so swapping to a BSP later would touch
only the sender — the engine and routing stay unchanged.

---

## 8. Data architecture

Relational, tenant-scoped. Relationships (`1───*` = one-to-many):

```
Tenant ─1───*─ FlowStep ─1───*─ FlowOption
  │                ▲                  │ next_step (0..1; NULL = terminal)
  │                └──────────────────┘
  │
  ├─1───*─ Session ─1───*─ Message
  │            └─ current_step ──► FlowStep (0..1)
  │
AuditLog ─*───1─ auth.User   (stands apart from tenant data)
```

**Tables** (implemented; see app `models.py` for the source of truth):

- **tenants** — id, name, wa_phone_number (unique), ig_account_id (unique),
  greeting_message, closing_message, handoff_enabled, handoff_email, is_active,
  created_at. *Token fields (`wa_access_token`, `ig_access_token`) are added in D1-06 as
  encrypted columns (SEC-02) — deliberately absent until encryption lands.*
- **flow_steps** — id, tenant_id (FK), label, message_text, is_start, is_terminal,
  created_at. **DB constraint:** at most one `is_start=true` per tenant (partial unique).
  "Exactly one" is completed by activation-time validation (D1-23).
- **flow_options** — id, step_id (FK), button_label (≤ 20 chars), next_step_id (FK,
  nullable = terminal). Deleting a referenced next step sets it NULL (becomes terminal).
- **sessions** — id, tenant_id (FK), channel, customer_identifier, current_step_id (FK,
  nullable), status (active|completed|handed_off), started_at, updated_at. **Accessed via
  `select_for_update()` during flow execution (D-105).** Indexed on
  (tenant, channel, customer_identifier) — the hot inbound lookup.
- **messages** — id, session_id (FK), direction (inbound|outbound), content, channel,
  provider_message_id (inbound), sent_at. **Unique (session, provider_message_id)** for
  idempotency (D-104). Since a session is one tenant+channel+customer, this satisfies the
  dedup intent; the worker also checks-before-process as the primary guard.
- **audit_logs** — id, admin_user_id (FK auth.User), action, entity_type, entity_id,
  diff (JSON), created_at. Append-only (FR-19 / SEC-05).

**Data lifecycle:** a new conversation always creates a new session (never reused, D-05).
No cross-conversation memory is retained.

---

## 9. Key processing flows

### 9.1 Webhook verification (one-time setup, WA-04)
Meta sends a **GET** to `/webhook` with a challenge; the endpoint echoes `hub.challenge`
after checking the configured verify token. Failure → no verification.

### 9.2 Inbound message (every message)

```
Meta ──POST /webhook──► Web process
   │  1. verify HMAC-SHA256 signature (SEC-01)   invalid → 200, log, discard
   │  2. extract channel, tenant id, customer id, payload
   │  3. resolve tenant                          unknown → 200, log, discard
   │  4. enqueue event ──► Redis
   └─ return HTTP 200 (< 5s)                      (ERR-01)

Redis ──► Celery worker
   │  5. lock + get/create session (D-105 row lock)
   │  6. dedup: seen provider_message_id? → ack & skip (D-104)
   │  7. FREE TEXT  → resend current step's message + buttons (no advance)  [FR-08]
   │     BUTTON     → match flow_option → advance session to next_step      [FR-07]
   │  8. TERMINAL (next_step NULL):
   │        handoff_enabled → send "Talk to a human" offer                  [FR-11]
   │        else            → send closing message, mark completed          [FR-12]
   │  9. NON-TERMINAL → load next step's message + options → send → log     [FR-09]
   ▼
PostgreSQL
```

**Numbered invariant (the canonical sequence), preserved from the PRD:**
1. Meta POSTs `/webhook`. Validate signature. Invalid → 200, log, discard.
2. Extract channel, tenant id, customer id, payload.
3. Look up tenant. Not found → log, discard, return 200.
4. Push to queue. Return 200. All further processing async.
5. Worker picks up; looks up or creates session (customer+tenant+channel).
6. Free text → resend current step's message + buttons. Don't advance.
7. Button reply → find matching `flow_option`; advance session to `next_step_id`.
8. `next_step_id` null (terminal) → if handoff enabled, send handoff offer; else send closing message, mark complete.
9. Not terminal → load next step's message + options; send; log outbound.

### 9.3 Outbound send (C-04)
Resolve per-tenant credentials (decrypt token) → check WhatsApp 24h window (WA-03;
> 23h since last customer message → flag + skip interactive) → render buttons/list within
limits (WA-02) → call Meta API → handle errors (ERR-03: no retry on 4xx, retry once on
5xx) → log outbound message.

---

## 10. API surface

| Surface | Endpoint(s) | Auth | Notes |
|---------|-------------|------|-------|
| **Webhook** | `GET /webhook` (verify), `POST /webhook` (events) | HMAC signature (POST) + verify token (GET) | Public; always returns 200. Channel-routed by payload. |
| **Admin API** (C-06) | `/api/...` tenant CRUD, flow config, toggles, log read | JWT; 401 if unauth (SEC-05) | Backs the React SPA; product-owner only. Every screen maps to endpoints here. |
| **React SPA** (C-07) | static app → calls the Admin API | JWT (login at AP-01) | The product UI (Relay). HTTPS only (SEC-03). |
| **Django admin** | `/admin/...` | Login required | Internal dev/debug only — not the product UI (D-107). |

The webhook is the only public, unauthenticated entry point — and it is protected by
signature verification, not by being secret.

---

## 11. Concurrency, resilience & production hardening

**Resilience rules (ERR-01..04):**
- Webhook always returns 200 to Meta; failures handled internally.
- Queue jobs retry ≤ 3× exponential backoff → dead-letter + alert.
- Meta API send error: log; don't retry 4xx; retry once on 5xx.
- Session `current_step_id` points to deleted step → reset to start, send greeting, log recovery.

**Cross-cutting hardening (D-104/105/106) — not optional polish:**
- **Idempotency (D-104).** Meta retries webhooks; the same message *will* arrive twice.
  Store the provider message id; dedup before processing. Prevents double-advancing.
- **Session concurrency (D-105).** Flow execution reads + advances session state inside a
  DB transaction with `select_for_update()` on the session row, so near-simultaneous
  messages for one session serialize. Needs Postgres row locking in any shared env
  (SQLite = dev only).
- **Secrets in prod (D-106).** Encryption key + tokens come from a managed secrets store
  (KMS/Vault) injected as env vars in prod; `.env` is dev-only. No code change dev↔prod.

---

## 12. Multi-tenancy & isolation (FR-20/21)

- **Logical isolation by tenant FK.** Every flow, session, message, and credential is
  scoped to a tenant. There is no shared mutable state across tenants.
- **No redeploy to add a tenant (FR-21).** Onboarding is data entry (admin panel), not a
  code change.
- **Blast-radius containment.** A misconfigured flow for one tenant cannot affect another;
  queries never cross the tenant boundary. (Enforcement detail in `security.md`.)

---

## 13. Scalability path (1–10 → 50+ tenants)

The design is deliberately small for v1 but unblocks growth by changing *operations*, not
*architecture*:

| Pressure point | v1 | Scale lever (no rewrite) |
|----------------|----|--------------------------|
| Inbound volume | 1 web process (Railway) | Add web replicas (stateless) |
| Processing throughput | 1 django-q2 worker (same deploy) | Split the worker to its own Railway service; raise worker count |
| Queue backend | DB-backed (django-q2) | Move to Redis / a managed queue if DB contention appears (task code unchanged) |
| Database | Supabase (single) | Connection pooling (PgBouncer), read replicas for log views, or paid tier |
| Flow engine | Stateless | Already horizontal — state is in DB |

**Always-on caveat:** webhooks require a host that never sleeps. We chose Railway (D-108)
precisely because free sleeping hosts cold-start and miss Meta's 5s window. Pure serverless
would need a managed queue + serverless consumers — more complex; not chosen for v1.

---

## 14. Environments & configuration

Same code in every environment; only env vars differ (12-factor). Settings split:
`config/settings/{base,dev,prod}.py`.

| Variable | Purpose | Dev | Prod |
|----------|---------|-----|------|
| `DJANGO_SETTINGS_MODULE` | which settings | `config.settings.dev` | `config.settings.prod` |
| `DJANGO_SECRET_KEY` | Django crypto | dev placeholder | secrets store |
| `DEBUG` | debug mode | `True` | `False` |
| `DJANGO_ALLOWED_HOSTS` | host allowlist | localhost | real hosts |
| `DATABASE_URL` | Postgres DSN (also the django-q2 broker) | unset → SQLite fallback | Supabase |
| `FERNET_KEY` (D1-06) | token encryption key | dev key in `.env` | **Railway secret, never DB** (D-106) |
| `RESEND_API_KEY` / email | handoff email | sandbox key | Railway secret |
| `META_APP_SECRET` / webhook verify token | webhook HMAC + GET verify | sandbox | Railway secret |

django-q2 needs no separate broker URL — it uses the database (`DATABASE_URL`). On Railway,
prod secrets are injected as environment variables (D-106).

`.env` is git-ignored and dev-only. Production injects secrets from a managed store.

---

## 15. Observability & operations

To meet 99.5% uptime (NFR-02) and the 3s latency target (NFR-01):

- **Logging.** Structured logs; **never customer PII** — use session id / hashed
  identifier (SEC-04). Log webhook verification failures, tenant-not-found discards,
  send errors, and recovery events.
- **Metrics to watch.** Webhook ack latency, queue depth, task failure rate,
  dead-letter count, Meta API error rate, 24h-window skips.
- **Alerting.** Dead-letter arrivals and availability failures alert the product owner
  (ERR-02 / NFR-02).
- **Health.** Liveness/readiness on the web process; worker heartbeat.
- **Tracing a conversation.** Session id is the correlation key across logs and the
  `messages` table (the conversation-log viewer, FR-18, reads this).

---

## 16. Non-functional requirements mapping

| NFR | Target | How the architecture meets it |
|-----|--------|-------------------------------|
| NFR-01 | < 3s response | Fast webhook ack + async processing; indexed session lookup; minimal work per step |
| NFR-02 | 99.5% uptime | Managed Postgres/Redis; multiple stateless web/worker processes; alerting on dead-letter/health |
| NFR-03 | Security | Signature validation on all webhooks; PII minimization — see `security.md` |
| NFR-04 | 1–10 → 50+ | Stateless tiers, env-driven config, extractable modules, swappable broker (§13) |
| NFR-05 | Auditability | `audit_logs` records every product-owner config/flow action with actor + timestamp |

---

## 17. Security (summary)

Full detail in [`security.md`](security.md). The invariants, in one place:
- **SEC-01** Verify every Meta webhook with HMAC-SHA256 before any processing.
- **SEC-02** Tenant tokens encrypted at rest; key never in the DB; never logged.
- **SEC-03** Admin panel over HTTPS only.
- **SEC-04** No customer PII in logs — session id / hashed identifier.
- **SEC-05** Admin endpoints reject unauth (401); all admin actions audited.

---

## 18. Open technical decisions

Tracked in [`decisions.md`](decisions.md). Currently blocking downstream work:
- **D-100** credential encryption mechanism (recommend Fernet) → blocks token fields / sender
- **D-101** Meta BSP selection → blocks all WhatsApp integration
- **D-102** Instagram interactive-message capability → blocks Instagram renderer
- **D-103** live-flow-edit behaviour for active sessions → blocks flow builder

Decided and in force: **D-001** (Django stack), **D-104** (idempotency), **D-105**
(session locking), **D-106** (prod secrets).
