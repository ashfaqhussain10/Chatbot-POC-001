# context/task_queue.md — Task Queue

> Owner: Senior writes; Juniors execute. PIER **Identify** tags drive sequencing.
> AI juniors get **only their task** + the named context slice — never the whole repo.

## Tags (PIER — Identify)
- `[S]` **Shared** — foundational; everything else depends on it. Build first, alone.
- `[P]` **Parallel** — independent; can run at the same time as other `[P]` work.
- `[D]` **Dependent** — needs one or more `[S]`/`[P]` items done first. Build last.

## Execution order (PIER — Execute)
**Build `[S]` → run `[P]` in parallel → then `[D]` sequentially.**

---

## Backlog

### `[S]` Shared — build first (blocks everything)
| ID | Task | Owner | Context slice | Done when |
|----|------|-------|---------------|-----------|
| T-S1 | Resolve open decisions D-100..D-103 (BSP, IG, encryption, live-flow) | Dev 1/2 + PO | decisions.md | All 4 marked DECIDED |
| T-S2 | Django project skeleton + 6 apps + settings/Celery wiring | Dev 1 | architecture.md | `manage.py runserver` boots |
| T-S3 | Data models + migrations (tenants, flow_steps, flow_options, sessions, messages, audit_logs) | Dev 1 | architecture.md §Data models | Migrations apply; tokens encrypted |
| T-S4 | Auth scaffolding + audit-log plumbing + one example DRF endpoint | Dev 1 | CLAUDE.md §7 | 401 on unauth; example endpoint copyable |

### `[P]` Parallel — after Shared
| ID | Task | Owner | Context slice | Done when |
|----|------|-------|---------------|-----------|
| T-P1 | Webhook receiver + HMAC-SHA256 validation + tenant routing + queue push | Dev 2 | flow steps 1–4, SEC-01 | Verified webhook returns 200 < 5s |
| T-P2 | Flow engine (load flow, current step, branching, free-text resend) | Dev 1 | flow steps 5–9, FR-05..10 | Engine unit-tested, stateless |
| T-P3 | Admin CRUD: tenant create/edit/deactivate + config screens (Django admin) | Dev 3 | FR-15/16, AP-01 | PO can manage tenants in admin |
| T-P4 | Conversation-log viewer (read-only) | Dev 3 | FR-18 | Logs visible per tenant |
| T-P5 | Seed data + test fixtures | Dev 3 (AI junior ok) | architecture.md | One demo tenant + sample flow |

### `[D]` Dependent — after the above
| ID | Task | Owner | Depends on | Done when |
|----|------|-------|------------|-----------|
| T-D1 | Message sender + WhatsApp 24h window enforcement | Dev 2 | T-P2 | Sends per tenant; flags >23h |
| T-D2 | Flow builder UI (form-based: steps, options, mark start; validate AP-03) | Dev 1 (+Dev 3 pair) | T-P2, D-103 | Invalid flows not activatable |
| T-D3 | Handoff service (email trigger, mark handed_off, confirmation) | Dev 1 + Dev 3 | T-P2 | Email sent; bot stops in session |
| T-D4 | Instagram renderer (or numbered-menu fallback) | Dev 2 | T-D1, D-102 | IG flow works per approved UX |
| T-D5 | End-to-end integration + hardening + security review | All | all above | Full inbound→handoff path green |

---

## How to brief an AI junior (sub-agent)
1. Give it **one task row** above + only the named context slice.
2. State success criteria (the "Done when" column).
3. Require: tests, Karpathy §4 compliance, no secrets/PII.
4. A human Senior reviews before merge. Juniors do **not** touch §7 security items.
