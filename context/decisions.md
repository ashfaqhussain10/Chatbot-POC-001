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

## D-102 — Instagram interactive message types (T-02)   [OPEN]
Date: 2026-06-03 · Owner: Dev 2
Context: Must assess current Instagram DM API button/quick-reply support and report to
product owner **before** building the Instagram flow renderer. If unsupported, fallback
is a numbered text menu (`1`/`2`/`3`), Instagram-only (IG-02).
Decision: —
Consequences: Blocks Instagram renderer. Product owner must approve fallback UX.

## D-101 — Meta BSP selection (T-01)   [OPEN]
Date: 2026-06-03 · Owner: Product owner + Dev 2
Context: Must pick a Meta BSP before **any** WhatsApp work begins. Options: 360dialog,
Twilio, Gupshup. BSP choice changes API endpoint format and auth method. Note: Meta/BSP
onboarding can take 1–2 weeks of waiting — start day 1.
Decision: —
Consequences: Blocks all WhatsApp integration (FR-01, C-01/C-04).

## D-100 — Credential encryption approach (T-04)   [OPEN]
Date: 2026-06-03 · Owner: Dev 1
Context: Which encryption mechanism + key-management strategy for Meta access tokens.
Tokens encrypted at rest; key must **not** live in the DB (SEC-02).
Decision: —
Consequences: Blocks tenants model finalization + message sender auth.

---

## D-001 — Backend stack = Django + DRF   [DECIDED]
Date: 2026-06-03 · Owner: Team
Context: PRD left stack to the team (Node vs Python recommended).
Decision: **Django + DRF**, Celery + Redis, PostgreSQL. Django admin covers admin CRUD/
config/log views cheaply; custom views only for the flow builder.
Consequences: Sets repo layout and conventions (see CLAUDE.md §6, architecture.md).
