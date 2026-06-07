# Security & Access Document

> **Owner:** Senior (reviewed by Dev 1 + Dev 2). Defines what we protect, from whom, and
> how. The guardrails here (SEC-01..05) are **invariants, never delegated to an AI junior
> or to Dev 3**, and are checked on every relevant PR. Pairs with
> [`architecture.md`](architecture.md) and [`decisions.md`](decisions.md).

---

## 1. Purpose & scope

This document is the single source of truth for the platform's **security posture** and
**access model**. It covers: what assets we protect, the threats we design against, the
controls that enforce each guardrail, the authentication/authorization model, secrets and
credential handling, PII/logging rules, audit, and a per-PR checklist.

Out of scope: infrastructure hardening of the chosen cloud provider (follow the provider's
baseline) and the frontend spec.

---

## 2. Security principles

1. **Verify, don't trust the edge.** The webhook is public; every payload is
   cryptographically verified before any processing.
2. **Least data, least exposure.** Store PII only where operationally necessary; keep it
   out of logs entirely.
3. **Secrets never live in the code or the database.** Encryption keys come from the
   environment / a managed store; tenant tokens are encrypted at rest.
4. **Tenant isolation is a security boundary**, not just a data convenience.
5. **Everything privileged is authenticated and audited.** No anonymous admin actions;
   every change is attributable.
6. **Fail safe and quiet.** On error, return the minimum to the caller (HTTP 200 to Meta),
   log internally, and never leak internals or secrets in responses.

---

## 3. Assets & threat model

**Assets we protect:**
- Tenant **Meta access tokens** (can send messages as the business — highest value).
- The **encryption key** that protects those tokens.
- **Customer PII** (phone numbers / IG handles, message content).
- **Flow & config integrity** (a tampered flow misroutes real customers).
- **The admin panel** (full control of every tenant).

**Primary threats & the control that addresses each:**

| Threat | Control | Guardrail |
|--------|---------|-----------|
| Forged / replayed webhooks | HMAC-SHA256 verification + idempotency | SEC-01, D-104 |
| Token theft from DB/backups/logs | Encryption at rest; key outside DB; never logged | SEC-02 |
| Eavesdropping on admin traffic | HTTPS only | SEC-03 |
| PII leak via logs | No PII in logs; session id / hashed identifier | SEC-04 |
| Unauthorized admin access | Auth required; 401 on unauth; audited | SEC-05 |
| Cross-tenant data access | Tenant-scoped queries; isolation by FK | FR-20 |
| Secret sprawl in prod | Managed secrets store; env injection | D-106 |

We are **not** defending against a malicious product owner (they are the trusted single
admin in v1) nor building DDoS protection beyond the cloud LB baseline.

---

## 4. Webhook security (SEC-01)

- **Every** inbound Meta webhook (`POST /webhook`) is verified with **HMAC-SHA256** over
  the **raw request body** using the Meta app secret, compared to the signature header,
  **before any parsing or processing**.
- Invalid signature → return **HTTP 200**, log the rejection (no PII), **discard**. We
  return 200 even on rejection so Meta does not retry a forged request indefinitely
  (ERR-01).
- Use a **constant-time comparison** for the signature check (no early-exit string compare).
- **Verification handshake (WA-04):** `GET /webhook` echoes `hub.challenge` only after the
  configured verify token matches.
- **Idempotency (D-104):** store the provider message id; a duplicate delivery is acked and
  skipped so retries cannot double-advance a customer.

**Never delegated.** Signature validation is a Dev 2 Senior task; AI juniors do not write it.

---

## 5. Credential management & encryption at rest (SEC-02)

- Tenant **`wa_access_token` / `ig_access_token` are encrypted at rest.** They are
  deliberately **absent from the data model until D1-06**, so no plaintext token can be
  stored in the interim.
- **Mechanism (D-100, recommended Fernet):** symmetric authenticated encryption
  (`cryptography` Fernet). Application encrypts on write, decrypts only at send time.
- **Key management:** the encryption key is sourced from the **environment** (`FERNET_KEY`),
  which in production comes from a **managed secrets store** (cloud KMS / Secrets Manager /
  Vault) — **never stored in the database**, never committed (D-106).
- **No token ever appears** in `__repr__`, `__str__`, admin display, logs, error messages,
  or API responses.
- **Key rotation (forward plan):** support re-encrypting tokens under a new key without
  schema change (envelope/versioned key id) — not required for v1 but the field design
  should not preclude it.

**Never delegated.** Encryption + key handling is a Dev 1 Senior task.

---

## 6. Transport security (SEC-03)

- The admin panel and admin API are served **over HTTPS only**.
- Production settings (`config/settings/prod.py`) enforce: `SECURE_SSL_REDIRECT`,
  `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS (`SECURE_HSTS_SECONDS` +
  subdomains + preload), and `SECURE_PROXY_SSL_HEADER` for LB-terminated TLS.
- The webhook endpoint is likewise HTTPS (Meta requires it).

---

## 7. PII & logging (SEC-04)

- **Customer PII must not appear in application logs.** Use the **session id** or a
  **hashed identifier** as the correlation key instead of phone numbers / IG handles.
- Message **content is stored** in the `messages` table (operationally necessary for the
  conversation-log viewer, FR-18) but is **not** echoed into logs.
- Token values, encryption keys, and signatures are never logged.
- Log lines that reference a conversation use the session id so support can trace a flow
  without exposing the customer.
- **Data minimization:** store only what the flow and handoff require (PRD: "PII stored
  only where operationally necessary").

---

## 8. Authentication & authorization

**Admin panel & API (AP-01, SEC-05):**
- Authentication **required**; **no public registration**. A single product-owner account
  is sufficient for v1.
- Session-based (Django) or JWT for the API; **all admin API endpoints reject
  unauthenticated requests with 401**.
- Passwords subject to Django's validators; secure, HTTPS-only cookies in prod.

**Authorization model (who can do what):**

| Actor | Access | Mechanism |
|-------|--------|-----------|
| **Product owner** | Full: tenant CRUD, flow config, logs | Authenticated admin login |
| **Business client** | **None** (no login in v1) | Requests changes via product owner |
| **End customer** | **None** — only messages via Meta | Never reaches the platform directly |
| **Human agent** | **None** in-platform | Receives handoff email; follows up outside the platform |
| **Webhook (Meta)** | Submit events only | Signature-verified; no account |

There is exactly one privilege level in v1 (product owner). If multi-admin or per-tenant
roles are needed later, introduce RBAC then — not now (avoid speculative complexity).

---

## 9. Audit & accountability (SEC-05 / FR-19)

- **Every product-owner action** on config and flows is recorded in **`audit_logs`** with
  actor (`admin_user`), action, entity type/id, a JSON diff, and timestamp.
- The log is **append-only** (no edit/delete through the app).
- **Auto-recording wiring** lands with auth (D1-11), since the actor identity comes from
  the authenticated session; the `audit_logs` table already exists to receive it.
- Audit entries are reviewable read-only in the admin (built by Dev 3).

---

## 10. Multi-tenant isolation as a security control (FR-20)

- All domain queries are **tenant-scoped by foreign key**; no code path returns another
  tenant's flows, sessions, messages, or credentials.
- A misconfiguration or compromised flow for one tenant **cannot affect another**.
- Per-tenant credentials are isolated rows; the message sender resolves credentials by
  tenant at send time and never caches across tenants.
- Reviewers must confirm new queries on tenant-owned tables include the tenant filter.

---

## 11. Secrets management (D-106)

| Environment | Secret source | Notes |
|-------------|---------------|-------|
| **Dev** | `.env` (git-ignored) | Convenience only; dev-grade values |
| **Prod** | Managed secrets store (KMS / Secrets Manager / Vault) → injected as env vars | Encryption key, Meta app secret, tenant token key material, email API key |

- `.env` is in `.gitignore`; `.env.example` documents keys with **no real values**.
- The application reads all secrets from the environment, so **no code differs** between
  dev and prod — only the source of the values.
- Secrets are **never** committed, logged, or written to the database.

---

## 12. Error handling & information disclosure

- Webhook always returns **HTTP 200** to Meta; internal failures are handled
  asynchronously (ERR-01) and never surfaced to the caller.
- Outbound Meta API errors are logged (without secrets); **4xx not retried, 5xx retried
  once** (ERR-03).
- `DEBUG=False` in production — no stack traces or settings leaked in responses.
- Generic error responses externally; detail stays in internal logs.

---

## 13. Security checklist (Definition of Done — apply per PR)

A change touching any of these areas is not done until:

- [ ] **SEC-01** — webhook signature verified (HMAC-SHA256, raw body, constant-time) before processing.
- [ ] **SEC-02** — no plaintext tokens; encryption used; key from env, not DB; tokens never logged.
- [ ] **SEC-03** — admin/API paths HTTPS-only (prod settings honored).
- [ ] **SEC-04** — no customer PII in logs; session id / hash used.
- [ ] **SEC-05** — admin endpoints 401 on unauth; admin actions land in `audit_logs`.
- [ ] **FR-20** — new queries on tenant-owned tables are tenant-scoped.
- [ ] **D-104** — inbound processing is idempotent (dedup on provider message id).
- [ ] No secrets in the diff (`.env`, keys, tokens); `.env.example` updated if keys added.
- [ ] Reviewed by a **Senior** (Dev 1 or Dev 2) for anything in §4, §5, §8.

---

## 14. Guardrail → enforcement map

| Guardrail | Enforced in | Verified by |
|-----------|-------------|-------------|
| SEC-01 webhook HMAC | `channels` webhook receiver (D2-04) | Unit test with valid/forged signatures |
| SEC-02 token encryption | `tenants` model + crypto util (D1-06) | Test: ciphertext at rest; no key in DB; no token in logs |
| SEC-03 HTTPS only | `config/settings/prod.py` | Settings review / deploy check |
| SEC-04 no PII in logs | logging conventions across apps | Log review; grep for identifiers in tests |
| SEC-05 auth + audit | auth scaffold (D1-11) + `audit_logs` (D1-09) | Test: 401 unauth; audit row on admin change |
| FR-20 isolation | tenant FK + scoped queries | Test: cross-tenant access returns nothing |
| D-104 idempotency | dedup constraint + worker check | Test: duplicate message id ignored |
| D-106 prod secrets | env-sourced settings | Deploy review; no secrets in repo |
