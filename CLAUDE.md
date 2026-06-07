# CLAUDE.md — Team Operating Guide

> This file is read automatically by every team member's Claude.
> It defines **how we work** (process + behavior), not just what we build.
> Project-specific facts live in [`context/`](context/). Read those too.

---

## 1. Project context

We are building a **multi-tenant, rule-based chatbot platform** that is the first
point of contact for customers messaging a business on **WhatsApp or Instagram**.
Conversation flows are driven entirely by **buttons / quick replies** — no NLP, no
free-text parsing. A single **product owner** configures everything through an admin
panel; business clients have no login. v1 targets **1–10 tenants**.

Full requirements: [`context/prd.md`](context/prd.md).
Architecture: [`context/architecture.md`](context/architecture.md).

---

## 2. Operating model — PIER

Every task, regardless of size, moves through **P → I → E → R**. This never changes.

| Step | What happens | Gate |
|------|--------------|------|
| **P — Plan**     | Claude analyzes the requirement and proposes a plan. | **Human approves the plan.** |
| **I — Identify** | Tag the work: `[S]` Shared · `[P]` Parallel · `[D]` Dependent. | — |
| **E — Execute**  | Build `[S]` first → run `[P]` in parallel → then `[D]` sequentially. | — |
| **R — Review**   | Integrate, test, report. | **Human approves final output.** |

### 🔑 Golden Rule
**Claude never writes code until a human says "IMPLEMENT."**
Planning, questions, and analysis are always allowed. Code is not — until approved.

### Tier
We run **one tier for everything: T3 (full PIER on every task).**
Process is uniform, but **effort is proportionate** — a one-line change gets a
one-line plan, not a ceremony. Uniform process ≠ uniform overhead.

---

## 3. Roles & ownership (hybrid: humans + AI juniors)

Humans own modules. **AI sub-agents act as the "juniors"** — they do repetitive /
boilerplate work under a human's direction, with **minimal context** (only their task).

| Human | Role | Owns |
|-------|------|------|
| **Dev 1** | Architect + Senior | DB schema, credential encryption, multi-tenancy, **flow engine**, **flow builder**, auth scaffolding |
| **Dev 2** | Senior | Webhook receiver + **signature validation**, message queue, message sender + **WhatsApp 24h window**, Instagram |
| **Dev 3** | Junior | Admin CRUD, config screens, conversation-log viewer, handoff email content, seed/test data |

**AI juniors (sub-agents):** boilerplate (serializers, CRUD endpoints from a template,
test fixtures, repetitive UI). Always directed by a human who reviews the output.

**Never delegated to an AI junior or to Dev 3:** anything in §7 (security guardrails),
flow-engine state logic, or the WhatsApp 24h-window enforcement.

---

## 4. Behavioral guidelines (Karpathy)

> Behavioral guidelines to reduce common LLM coding mistakes.
> **Tradeoff:** these bias toward caution over speed. For trivial tasks, use judgment.

### 4.1 Think Before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 4.2 Simplicity First
**Minimum code that solves the problem. Nothing speculative.**
- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.
- Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 4.3 Surgical Changes
**Touch only what you must. Clean up only your own mess.**
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.
- Remove imports/variables/functions that *your* changes made unused.
- The test: every changed line traces directly to the request.

### 4.4 Goal-Driven Execution
**Define success criteria. Loop until verified.**
- "Add validation" → "Write tests for invalid inputs, then make them pass."
- "Fix the bug" → "Write a test that reproduces it, then make it pass."
- "Refactor X" → "Ensure tests pass before and after."
- For multi-step tasks, state a brief plan with a verify step for each.

**Working if:** fewer unnecessary diffs, fewer rewrites from overcomplication, and
clarifying questions come *before* implementation rather than after mistakes.

---

## 5. Context & team memory

The [`context/`](context/) folder is shared team memory. Who writes what:

| File | Owner | Purpose |
|------|-------|---------|
| `context/prd.md` | PRD | Product requirements (source of truth for *what*). |
| `context/architecture.md` | Architect (Dev 1) | Technical architecture (the *how*). |
| `context/security.md` | Senior | Security & access model; guardrails (SEC-01..05). |
| `context/frontend_spec.md` | Dev 1 / Dev 3 | "Relay" admin panel UI spec (React SPA). |
| `context/decisions.md` | Senior | Running decision log (ADR-style). |
| `context/task_queue.md` | Senior → Juniors | Tagged backlog (`[S]/[P]/[D]`) for execution. |

**Key rule:** AI juniors see **only their task** (minimal context). The Senior /
Architect sees everything. When briefing an AI junior, give it the single task and
the relevant slice — not the whole repo.

---

## 6. Tech stack & conventions

- **Backend:** Django + Django REST Framework (DRF)
- **Async/queue:** **django-q2** (database-backed — no Redis) (D-108)
- **Database:** **PostgreSQL via Supabase** (free, always-on) (D-108)
- **Frontend:** **custom React SPA** ("Relay" design) against the DRF API, JWT auth (D-107).
  Django admin is kept for **internal dev/debug only**, not the product UI.
- **Email (handoff):** Django email → **Resend / Brevo** (D-108)
- **Hosting:** **Railway** (always-on app + worker, ~$5/mo) · Supabase (DB) ·
  Cloudflare Pages/Vercel (SPA) (D-108)
- **Python:** 3.11 · **Style:** `ruff` + `black` · **Tests:** `pytest` + `pytest-django`

Repo layout (target): `config/` (Django project), `apps/{tenants,flows,conversations,channels,handoff,audit}/`, `frontend/` (React SPA), `context/`, `docs/`.

---

## 7. Security guardrails — NON-NEGOTIABLE

These are never delegated to an AI junior and always reviewed by a Senior:

- **SEC-01** Verify every Meta webhook with **HMAC-SHA256** before any processing.
- **SEC-02** Tenant Meta tokens **encrypted at rest**; key never stored in the DB. Never log tokens.
- **SEC-03** Admin panel served over **HTTPS only**.
- **SEC-04** **No customer PII in logs** — use session ID / hashed identifier.
- **SEC-05** All admin API endpoints reject unauthenticated requests (401); all admin actions land in `audit_logs`.

---

## 8. Definition of Done

A task is done when:
1. Code matches its approved plan (PIER-R) and the Karpathy guidelines (§4).
2. Tests written and passing (`pytest`).
3. No secrets, no PII in logs, security checklist (§7) satisfied where relevant.
4. PR reviewed and approved by a **Senior** (Dev 1 or Dev 2).
5. `context/decisions.md` updated if the task resolved an open decision.
