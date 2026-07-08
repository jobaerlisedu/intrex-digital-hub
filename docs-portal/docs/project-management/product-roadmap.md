# Product Roadmap & Backlog

**Last updated:** 08-Jul-2026  
**Owner:** Product Management  
**Status:** Living document — updated each sprint review

---

## Vision

Transform Intrex Digital Hub from a feature-rich ERP into an **automated, event-driven enterprise platform** where routine financial, procurement, and certification workflows execute without manual intervention, and external systems synchronise in real time.

---

## Strategic Themes (Q3–Q4 2026)

| Theme | Objective | Success Metric |
|-------|-----------|----------------|
| **Process Automation** | Replace manual certificate issuance, journal posting, and notification workflows with Firestore-triggered Cloud Functions | Zero-touch certificate issuance; <30s from payment to certificate |
| **Integration Layer** | Enable external portals to subscribe to ERP state changes via webhooks | First external integration live (client-facing portal sync) |
| **Security Hardening** | Enforce audit log immutability, session lifecycle signals, and tamper-proof trails | Zero audit-log deletion incidents; all auth events logged |
| **Platform Stability** | Productionise Cloud Functions deployment, monitoring, and error recovery | Cloud Function uptime ≥ 99.9%; pager-duty alerts configured |

---

## Epics & User Stories

### Epic 1: Firestore Cloud Triggers (Automation Engine)

> **Priority: P1 (Critical)**  |  **Theme:** Process Automation  |  **Target Release:** Sprint 8–9

#### Story 1.1 — Auto-issue certificates on payment clearance

> **As an** EdTech administrator  
> **I want** certificates to be automatically issued when a learner's balance reaches zero and assessments are passed  
> **So that** learners receive credentials immediately without manual review.

**Acceptance Criteria:**
- [ ] Firebase Cloud Function triggered `onWrite` on `learn_payments`
- [ ] When `dueAmount ≤ 0` and assessment grade exists and is "Passed", write certificate record to `learn_certificates`
- [ ] When `dueAmount > 0` or grade is "Failed" or missing, no certificate is written
- [ ] Function logs outcome to Cloud Logging with structured payload
- [ ] Idempotent — multiple payment writes for the same enrollment do not create duplicate certificates
- [ ] Error handling: on failure, push error entry to a `failed_events` Firestore collection for manual retry

**Story Points:** 8  
**Dependencies:** Firestore collection schemas for `learn_payments`, `learn_course_assessments`, `learn_certificates` (all exist)

---

#### Story 1.2 — Slack notification on new requisitions

> **As a** procurement manager  
> **I want** a Slack notification sent to the procurement channel whenever a new approved requisition is created  
> **So that** my team can respond to procurement requests within the same business day.

**Acceptance Criteria:**
- [ ] Firebase Cloud Function triggered `onCreate` on `requisitions`
- [ ] Function reads requisition fields: `title`, `requestedBy`, `department`, `urgency`, `createdAt`
- [ ] Slack webhook URL stored in Firestore `config/slack_webhook` document
- [ ] Notification formatted with colour-coded urgency marker (red for high, yellow for medium, green for low)
- [ ] Non-blocking — webhook failure does not prevent the requisition write
- [ ] Configurable via Firestore config document (enable/disable, override channel)

**Story Points:** 5  
**Dependencies:** Slack workspace admin must provide incoming webhook URL; `requisitions` collection schema (exists)

---

#### Story 1.3 — Auto-post inventory valuation on goods receipt

> **As an** accounts officer  
> **I want** inventory valuation journal entries to be automatically created when a goods receipt is processed  
> **So that** the general ledger always reflects current stock value without manual journal entry.

**Acceptance Criteria:**
- [ ] Firebase Cloud Function triggered `onUpdate` on `goods_receipts` when status changes to `Received`
- [ ] Function retrieves product cost from `products` collection
- [ ] Creates a journal entry in `journal_entries` (Debit: Inventory Asset, Credit: GRN/AP Clearing)
- [ ] Maps to correct COA codes based on product category
- [ ] Includes `goods_receipt_id` cross-reference in journal entry metadata
- [ ] Reversal entry created if GRN is voided

**Story Points:** 8  
**Dependencies:** `goods_receipts` and `journal_entries` collections (exist); COA mapping table needed

---

### Epic 2: Security & Audit Hardening

> **Priority:** P1 (Critical)  |  **Theme:** Security Hardening  |  **Target Release:** Sprint 9

#### Story 2.1 — Audit log on login/logout

> **As a** security auditor  
> **I want** every user login and logout to be recorded in the audit log with IP address, user agent, and timestamp  
> **So that** I can investigate suspicious access patterns.

**Acceptance Criteria:**
- [ ] Django signal `user_logged_in` writes to `accounts_auditlog`: user, IP, user-agent, timestamp, event_type="LOGIN"
- [ ] Django signal `user_logged_out` writes equivalent record with event_type="LOGOUT"
- [ ] Existing active-session records are terminated on logout (remote device session invalidation)
- [ ] Audit log entries are append-only — no update/delete exposed via admin
- [ ] Logs include `tenant_id` for multi-tenant traceability

**Story Points:** 5  
**Dependencies:** Django `user_logged_in`/`user_logged_out` signals (built-in); `accounts_auditlog` model (exists)

---

#### Story 2.2 — Audit log immutability enforcement

> **As a** compliance officer  
> **I want** audit log entries to be impossible to delete from the system  
> **So that** we maintain a tamper-proof trail for regulatory audits.

**Acceptance Criteria:**
- [ ] `pre_delete` signal on `AuditLog` model raises `PermissionDenied` for all delete attempts
- [ ] Admin `delete` action is overridden/hidden for `AuditLog` model
- [ ] Bulk delete from queryset also blocked at model level
- [ ] Cascade deletes from parent model do not remove audit entries
- [ ] Error message returned to user: "Audit log entries cannot be deleted."
- [ ] Soft-delete / archival mechanism exists separately for data retention policies (non-destructive)

**Story Points:** 3  
**Dependencies:** `AuditLog` model (exists)

---

### Epic 3: Webhook Dispatcher Engine

> **Priority:** P2 (Important)  |  **Theme:** Integration Layer  |  **Target Release:** Sprint 10

#### Story 3.1 — Webhook registration CRUD

> **As an** integration engineer  
> **I want** to register, update, and deactivate webhook endpoints per event type  
> **So that** external systems can subscribe to ERP events without code changes.

**Acceptance Criteria:**
- [ ] Firestore collection `webhooks` with schema: `event_type`, `target_url`, `secret_token`, `is_active`, `created_at`, `updated_at`, `last_triggered_at`, `failure_count`
- [ ] Admin interface (Django admin) to manage webhook registrations
- [ ] Secret token auto-generated on creation (SHA-256 HMAC key)
- [ ] Validation on save: `target_url` must be valid HTTPS URL; `event_type` must match known event types
- [ ] Deactivated webhooks (`is_active = false`) are skipped during dispatch

**Story Points:** 5  
**Dependencies:** None (new collection)

---

#### Story 3.2 — Webhook dispatch on PO fulfilment

> **As a** client portal operator  
> **I want** to receive a signed POST notification when a Purchase Order is fulfilled  
> **So that** my portal can reflect the updated shipment status in real time.

**Acceptance Criteria:**
- [ ] Helper utility `dispatch_webhook(event_type, payload)` sends signed POST to all active webhooks registered for that event
- [ ] Payload signed with HMAC-SHA256 using per-webhook `secret_token`; signature sent in `X-Webhook-Signature` header
- [ ] Payload includes: `event_type`, `timestamp`, `data` (relevant document snapshot)
- [ ] On 2xx response: update `last_triggered_at`, reset `failure_count`
- [ ] On non-2xx or timeout: increment `failure_count`; auto-deactivate after 10 consecutive failures
- [ ] Dispatch is non-blocking — queued via background task (Celery or Django-Q)
- [ ] Retry logic: exponential backoff up to 3 retries
- [ ] Full dispatch log maintained in `webhook_delivery_log` collection

**Story Points:** 8  
**Dependencies:** Celery/Django-Q must be operational; `webhooks` collection (Story 3.1)

---

#### Story 3.3 — Event type registry

> **As a** developer  
> **I want** a central registry of all supported event types  
> **So that** webhook subscribers know which events are available and what payload shape to expect.

**Acceptance Criteria:**
- [ ] Event type registry defined as a Python enum or dict in a central module (`config/event_types.py`)
- [ ] Initial event types: `PO_FULFILLED`, `REQUISITION_CREATED`, `PAYMENT_RECEIVED`, `CERTIFICATE_ISSUED`, `INVOICE_POSTED`
- [ ] Each event type has: `name`, `description`, `schema_url` (link to docs), `version`
- [ ] Registry exposed via API endpoint `GET /api/v1/webhooks/events/` for programmatic discovery
- [ ] Admin interface to view registered event types (read-only)

**Story Points:** 3  
**Dependencies:** Story 3.1, Story 3.2

---

### Epic 4: Platform & Infrastructure

> **Priority:** P2 (Important)  |  **Theme:** Platform Stability  |  **Target Release:** Sprint 9–10

#### Story 4.1 — Cloud Functions deployment pipeline

> **As a** DevOps engineer  
> **I want** an automated CI/CD pipeline for deploying Cloud Functions  
> **So that** function updates are tested, versioned, and deployed without manual steps.

**Acceptance Criteria:**
- [ ] GitHub Actions workflow: on push to `main` with changes under `functions/`, deploy to Google Cloud Functions
- [ ] Workflow runs linting + unit tests before deployment
- [ ] Deployment uses `gcloud functions deploy` with env-specific config
- [ ] Secret environment variables (Slack webhook, etc.) pulled from Google Secret Manager
- [ ] Rollback capability via previous version tag

**Story Points:** 8  
**Dependencies:** Google Cloud project configured with billing; Firebase Admin SDK access

---

#### Story 4.2 — Monitoring & alerting for Cloud Functions

> **As a** platform engineer  
> **I want** dashboards and alerts for Cloud Function error rates, latency, and invocation counts  
> **So that** we can detect and respond to failures before users are impacted.

**Acceptance Criteria:**
- [ ] Cloud Monitoring dashboard created for all functions: invocation count, error count, execution time p50/p95/p99
- [ ] Alert policy: error rate > 5% over 5 minutes → PagerDuty/Opsgenie notification
- [ ] Alert policy: function timeout rate > 1% → slack notification to #devops
- [ ] All functions emit structured logs with `severity`, `function_name`, `execution_id`, `trigger_resource`
- [ ] Log-based metric for business-level failures (e.g., certificate generation failure)

**Story Points:** 5  
**Dependencies:** Story 4.1; Google Cloud Monitoring + PagerDuty setup

---

### Epic 5: Technical Debt & Housekeeping

> **Priority:** P3 (Nice-to-have)  |  **Theme:** Platform Stability  |  **Target Release:** Interleaved across sprints

#### Story 5.1 — Stylelint CSS auto-format pipeline (COMPLETED)

> ✅ Delivered as part of Sprint 5 cleanup. CSS files now pass Stylelint checks via `--fix`.

#### Story 5.2 — Centralise COA mapping

> **As an** accountant  
> **I want** Chart of Accounts codes to be centrally configured in Firestore  
> **So that** auto-posting functions always use the correct account codes without hardcoding.

**Acceptance Criteria:**
- [ ] Firestore document `config/coa_mapping` contains category-to-COA-code mappings
- [ ] Inventory valuation function reads COA from this config instead of hardcoded values
- [ ] Admin interface to view and update COA mappings
- [ ] Validation: mappings must reference valid COA codes that exist in `chart_of_accounts`

**Story Points:** 5  
**Dependencies:** Story 1.3 (will use this mapping)

---

## Release Plan

| Release | Sprint(s) | Focus | Stories |
|---------|-----------|-------|---------|
| **v2.1** | Sprint 8 | Certificate auto-issuance, Slack notifications | 1.1, 1.2 |
| **v2.2** | Sprint 9 | Inventory valuation, audit hardening | 1.3, 2.1, 2.2, 4.1 |
| **v2.3** | Sprint 10 | Webhook engine, event registry | 3.1, 3.2, 3.3, 4.2 |

---

## Backlog (Prioritised)

| Rank | Story | Epic | Priority | Story Pts | Sprint |
|------|-------|------|----------|-----------|--------|
| 1 | 1.1 — Auto-issue certificates | Cloud Triggers | P1 | 8 | S8 |
| 2 | 1.2 — Slack notifications | Cloud Triggers | P1 | 5 | S8 |
| 3 | 1.3 — Inventory valuation | Cloud Triggers | P1 | 8 | S9 |
| 4 | 2.1 — Audit log on login/logout | Security | P1 | 5 | S9 |
| 5 | 2.2 — Audit log immutability | Security | P1 | 3 | S9 |
| 6 | 4.1 — Cloud Functions CI/CD | Platform | P2 | 8 | S9 |
| 7 | 3.1 — Webhook CRUD | Webhooks | P2 | 5 | S10 |
| 8 | 3.2 — Webhook dispatch | Webhooks | P2 | 8 | S10 |
| 9 | 4.2 — Monitoring & alerting | Platform | P2 | 5 | S10 |
| 10 | 3.3 — Event type registry | Webhooks | P2 | 3 | S10 |
| 11 | 5.2 — Centralise COA mapping | Housekeeping | P3 | 5 | TBD |
| | **Total** | | | **71** | |

---

## Velocity & Capacity Planning

| Sprint | Available Days | Team Size | Est. Capacity (pts) | Planned Points | Load |
|--------|---------------|-----------|---------------------|----------------|------|
| S8 | 10 | 2 devs | 20 | 13 (1.1 + 1.2) | 65% |
| S9 | 10 | 2 devs | 20 | 16 (1.3 + 2.1 + 2.2) | 80% |
| S10 | 10 | 2 devs | 20 | 16 (3.1 + 3.2 + 4.2) | 80% |

**Assumption:** 2 full-time developers at 1 pt/dev-day. Actual velocity to be calibrated after Sprint 8.

---

## Key Dependencies & Blockers

| ID | Dependency | Affected Stories | Owner | Status |
|----|-----------|------------------|-------|--------|
| D1 | Google Cloud project with billing enabled | 1.1, 1.2, 1.3, 4.1 | Infrastructure | 🔴 Not started |
| D2 | Firebase Admin SDK deployed to Cloud Functions | 1.1, 1.2, 1.3 | Infrastructure | 🔴 Not started |
| D3 | Slack incoming webhook URL | 1.2 | Business Ops | 🟡 Awaiting stakeholder |
| D4 | Celery / Django-Q operational for async dispatch | 3.2 | Backend | 🔴 Not started |
| D5 | Google Secret Manager for env secrets | 4.1 | Infrastructure | 🔴 Not started |
| D6 | PagerDuty/Opsgenie account for alerting | 4.2 | DevOps | 🔴 Not started |

---

## Risk Register

| R# | Risk | Probability | Impact | Mitigation | Owner |
|----|------|-------------|--------|------------|-------|
| R1 | Google Cloud billing not approved | High | Critical | Escalate to management; prepare cost estimate | PM |
| R2 | Cloud Functions cold start latency | Medium | Medium | Use min-instance setting; benchmark before production | Backend |
| R3 | Webhook secret token exposure | Low | Critical | Auto-rotate via admin; store in Secret Manager only | Backend |
| R4 | Slack webhook rate limiting | Medium | Low | Batch notifications; queue-based dispatch | Backend |
| R5 | Team unfamiliar with Cloud Functions | Medium | Medium | Allocate 2 days spike/grooming in Sprint 8 | EM |

---

## Definition of Ready (DoR)

A story is ready for sprint planning when:
- [ ] Acceptance criteria are clear and testable
- [ ] Dependencies are identified and unblocked (or have a workaround)
- [ ] Technical spike completed (if needed)
- [ ] Story pointed by the team
- [ ] UI/UX mockups attached (if UI changes involved)
- [ ] API contract agreed (if API changes involved)

## Definition of Done (DoD)

A story is complete when:
- [ ] Code merged to `main` and deployed to staging
- [ ] Acceptance criteria all pass
- [ ] Unit tests written and passing (coverage ≥ 80%)
- [ ] Integration tests pass
- [ ] Linting & quality gates pass (ESLint, Stylelint, Ruff)
- [ ] API documentation updated (if applicable)
- [ ] Runbook updated (if ops impact)
- [ ] Product owner sign-off obtained
