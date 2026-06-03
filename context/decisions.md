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
