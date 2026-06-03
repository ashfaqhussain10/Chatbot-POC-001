# context/prd.md — Product Requirements (source of truth)

> Owner: PRD. This is the *what*. Extracted from `chatbot_platform_requirements.docx` v1.0.
> Status: Ready for dev. Stack: team-decided → Django/Python (see architecture.md).

## 1. Product overview
Multi-tenant, rule-based chatbot platform; first point of contact for customers
messaging a business via **WhatsApp or Instagram**. Flows are **button / quick-reply**
driven — no free-text parsing. Product owner configures everything. One WhatsApp
Business number per client.

## 2. Architecture decisions (D-01…D-06)
- **D-01** Flow logic = button/quick-reply menus only. No free-text parsing.
- **D-02** One WhatsApp number per business client.
- **D-03** Human handoff = per-client toggle, email delivery.
- **D-04** Configuration = product owner only. No client portal in v1.
- **D-05** Session persistence = flow restarts on return. No cross-conversation memory.
- **D-06** Closing message = configurable per client.

## 3. Stakeholders
- **S-01 Product owner** — onboards clients, configures flows, manages platform.
- **S-02 Business client** — deploys the bot; no login; requests changes via product owner.
- **S-03 End customer** — messages the business; never touches the platform.
- **S-04 Human agent** — business staff who receives handoff email, takes over manually.

## 4. Functional requirements

### 4.1 Channel integration
- **FR-01** Connect each client's WhatsApp Business number via WhatsApp Business API through a Meta BSP. Route inbound webhooks to the correct client by destination number.
- **FR-02** Connect each client's Instagram via Instagram Messaging API (linked FB Page + `instagram_manage_messages`).
- **FR-03** Verify all inbound Meta webhooks via signature validation before processing.
- **FR-04** Route inbound messages to the correct client's flow by channel identifier.

### 4.2 Conversation engine
- **FR-05** Send client's configured greeting on first inbound message, before options.
- **FR-06** All interaction via buttons/quick-replies; never expect free text as a flow decision.
- **FR-07** Branching: next step determined by which button was tapped.
- **FR-08** Free text mid-flow → resend current step's buttons with a prompt; don't advance/break.
- **FR-09** Returning customer (same number, new conversation) → restart from greeting; no prior session data.

### 4.3 Flow termination & human handoff
- **FR-10** End state = customer completes flow OR no further branches exist.
- **FR-11** End + handoff enabled → offer "Talk to a human" button; if tapped, email customer details, channel, timestamp, conversation path.
- **FR-12** End + handoff disabled → send configured closing message, end session.
- **FR-13** After handoff → send confirmation to customer, stop responding; agent follows up manually.
- **FR-14** Handoff toggle + email address configurable per client by product owner.

### 4.4 Admin panel
- **FR-15** Create/edit/deactivate client accounts (name, WA number, IG account ID, handoff email, active status).
- **FR-16** Configure per client: greeting, closing, handoff toggle, handoff email.
- **FR-17** Build/edit conversation flow per client: steps, button labels, branching. ⚠️ Most complex part.
- **FR-18** View per-client conversation logs: history, channel, timestamps, path.
- **FR-19** Log all admin actions with actor + timestamp (audit).

### 4.5 Multi-tenancy & isolation
- **FR-20** Logical isolation of each client's flows/conversations/credentials; one misconfig can't affect others.
- **FR-21** Adding a new client requires no redeployment.

## 5. Non-functional requirements
- **NFR-01** Latency — respond within 3s under normal load.
- **NFR-02** Availability — 99.5% uptime; failures alert product owner.
- **NFR-03** Security — webhook signature validation on all endpoints; PII stored only where necessary.
- **NFR-04** Scalability — v1 = 1–10 tenants; must not block scaling to 50+.
- **NFR-05** Auditability — all product-owner config/flow actions logged with actor + timestamp.

## 6. Out of scope (v1)
AI/NLP generation · client self-service portal · in-platform agent inbox · outbound
broadcast/campaigns · channels beyond WhatsApp/Instagram · in-chat payments ·
analytics dashboard (raw logs only) · mobile app.

## 7. Key platform constraints
- **WhatsApp 24h window** — interactive messages (buttons) only within 24h of customer's
  last message; outside, only pre-approved templates. v1: flag & log, don't send outside window.
- **WhatsApp buttons** — reply buttons ≤ 3 options; list messages ≤ 10; labels ≤ 20 chars.
- **Instagram buttons** — capability must be assessed (T-02); fallback = numbered text menu
  (`1`/`2`/`3`), Instagram sessions only, must not affect WhatsApp logic.
