# context/architecture.md — System Architecture

> Owner: Architect (Dev 1). The *how*. Keep in sync with code.

## Guiding principle
**Monolith with clean internal module boundaries.** Do not build microservices for
1–10 tenants. Structure modules so they *can* be extracted later — but do not extract now.

## Stack
| Concern | Choice | Notes |
|---------|--------|-------|
| Web/backend | **Django + DRF** | Webhooks + admin API in one project. |
| Async/queue | **Celery + Redis** | In-process for v1; swap broker to SQS later if load demands. |
| Database | **PostgreSQL** | Relational — flow data has structured relationships. |
| Admin UI | **Django admin** + custom flow-builder views | Admin gives CRUD/config/logs nearly free. |
| Email | Django email → **SendGrid/SES** | Transactional service, not raw SMTP. |
| Hosting | Any major cloud w/ **persistent workers** | Serverless alone insufficient for queue worker. |

## Modules (Django apps) ↔ components (C-01…C-08) ↔ owner

| Django app | Component | Responsibility | Owner |
|------------|-----------|----------------|-------|
| `channels` | C-01 Webhook receiver | Public HTTPS endpoint; validate signature; identify tenant; queue event. Respond 200 < 5s. | Dev 2 |
| `channels` | C-02 Queue | Celery decouples receipt from execution; retries + dead-letter. | Dev 2 |
| `flows` | C-03 Flow engine | Load tenant flow; determine current step; return next message + buttons. **Stateless** — all state in DB. | Dev 1 |
| `channels` | C-04 Message sender | Send via correct Meta API per tenant; enforce WhatsApp 24h window. | Dev 2 |
| `handoff` | C-05 Handoff service | On request: send email, mark session handed off, stop bot. | Dev 1 (backend) / Dev 3 (email content) |
| `tenants` + DRF | C-06 Admin API | Tenant CRUD, flow config, toggles, logs. Auth-protected. | Dev 1 (scaffold) / Dev 3 (endpoints) |
| Django admin | C-07 Admin panel | Web UI for product owner. Flow builder = hardest piece. | Dev 3 (CRUD) / Dev 1 (builder) |
| all apps | C-08 Database | Tenants, flows, sessions, logs, audit. | Dev 1 |

## Inbound message flow (must hold for every message)
1. Meta POSTs `/webhook`. Validate signature. Invalid → 200, log, discard.
2. Extract channel, tenant id, customer id, payload.
3. Look up tenant. Not found → log, discard, return 200.
4. Push to queue. Return 200. All further processing async.
5. Worker picks up; looks up or creates session (customer+tenant+channel).
6. Free text → resend current step's message + buttons. Don't advance.
7. Button reply → find matching `flow_option`; advance session to `next_step_id`.
8. `next_step_id` null (terminal) → if handoff enabled, send handoff offer; else send closing message, mark complete.
9. Not terminal → load next step's message + options; send; log outbound.

## Resilience rules (ERR-01…04)
- Webhook always returns 200 to Meta; failures handled internally.
- Queue jobs retry ≤ 3× exponential backoff → dead-letter + alert.
- Meta API send error: log; don't retry 4xx; retry once on 5xx.
- Session `current_step_id` points to deleted step → reset to start, send greeting, log recovery.

## Production hardening (cross-cutting) — D-104/105/106
These apply across modules; do not treat as optional polish.
- **Idempotency (D-104).** Meta retries webhooks; the same message *will* arrive twice.
  Store the provider message id; uniqueness per (tenant, channel, provider_message_id).
  Already-seen id → ack 200 and skip. Prevents double-advancing the flow.
- **Session concurrency (D-105).** Flow execution reads + advances session state inside a
  DB transaction with `select_for_update()` on the session row, so two near-simultaneous
  messages for one session serialize instead of racing. Needs Postgres row locking in any
  shared env (SQLite = dev only).
- **Secrets in prod (D-106).** Encryption key + tokens come from a managed secrets store
  (KMS/Vault) injected as env vars in prod; `.env` is dev-only. Settings read from env
  either way — no code change dev↔prod.

## Data models (section 8 of PRD)
- **tenants** — id, name, wa_phone_number, wa_access_token (enc), ig_account_id, ig_access_token (enc), handoff_enabled, handoff_email, greeting_message, closing_message, is_active, created_at
- **flow_steps** — id, tenant_id (FK), label, message_text, is_start, is_terminal, created_at. Exactly one `is_start=true` per tenant.
- **flow_options** — id, step_id (FK), button_label (≤20 chars), next_step_id (FK, nullable=terminal)
- **sessions** — id, tenant_id (FK), channel, customer_identifier, current_step_id (FK), status (active|completed|handed_off), started_at, updated_at. Accessed via `select_for_update()` during flow execution (D-105).
- **messages** — id, session_id (FK), direction (inbound|outbound), content, channel, provider_message_id (inbound; unique per tenant+channel for dedup, D-104), sent_at
- **audit_logs** — id, admin_user_id, action, entity_type, entity_id, diff (JSON), created_at
