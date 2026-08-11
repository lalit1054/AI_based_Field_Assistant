# Scope Document

## AI-Assisted Field Troubleshooting & Ticketing Platform (QR-Based)

| | |
|---|---|
| **Document Version** | 1.0 (Draft) |
| **Date** | 08 July 2026 |
| **Prepared By** | Lalit Kumar |
| **Status** | For Review |

---

## 1. Background

The company deploys multiple Intelligent Traffic System (ITS) applications — ANPR (Automatic Number Plate Recognition), AVC (Automatic Vehicle Classification), SVDS (Stationary Vehicle Detection System), and MLFF (Multi-Lane Free Flow tolling) — across multiple client sites, each with multiple lanes. When a failure occurs (device connectivity loss, API crash, application crash, camera fault, data mismatch, etc.), the current resolution flow depends on the site operator calling the support desk, describing the issue verbally, and waiting for an engineer to remotely inspect logs or travel to site. This is slow, error-prone, and generates poor-quality tickets with little diagnostic evidence.

## 2. Problem Statement

1. Site operators cannot identify which system/component has failed or why.
2. Issue reporting is manual (phone/WhatsApp/email), unstructured, and lacks proof.
3. Support engineers spend significant time on repeatable, known issues (service restart, cable reseat, disk full, NTP drift, etc.) that operators could fix themselves with guidance.
4. There is no central view of incidents across applications, sites, and lanes.

## 3. Proposed Solution (Concept)

Every deployed unit (per application, per site, per lane where applicable) carries a **QR sticker**. Scanning it with any smartphone opens a **central web application** (mobile-first PWA) where the user's context (application type → site → lane) is either **pre-encoded in the QR link** or selected via dropdowns. An **LLM-based diagnostic assistant** then:

1. Fetches recent logs, health metrics, and heartbeat status of that specific system.
2. Analyses them against a curated **knowledge base** (runbooks, SOPs, known-error database, OEM manuals) using RAG.
3. Explains **what likely happened** in plain language and gives **step-by-step self-fix guidance** appropriate for a non-technical operator.
4. If the user cannot resolve it, allows him/her to **raise a ticket in one tap**, auto-filled with context, diagnostic summary, chat transcript, and **one or more photos** as proof.

## 4. Objectives & Success Criteria

| # | Objective | Success Metric (target) |
|---|-----------|------------------------|
| O1 | Reduce Mean Time To Resolution (MTTR) for L1 issues | ≥ 40% reduction within 6 months of go-live |
| O2 | Enable operator self-service for known issues | ≥ 30% of incidents resolved without a ticket |
| O3 | Improve ticket quality | 100% of tickets carry system context + logs snapshot; ≥ 80% carry photos |
| O4 | Central visibility of incidents | Live dashboard across all sites/apps/lanes |
| O5 | Time from problem to structured report | < 3 minutes from QR scan to ticket/resolution start |

## 5. In Scope

### 5.1 QR & Context Resolution
- Unique QR code generation per asset (application instance / site / lane), encoding a signed asset ID in the URL.
- Fallback manual selection flow: Application Type → Site → Lane (lane shown only where applicable, e.g., ANPR/AVC per-lane; MLFF gantry-level).
- QR sticker artwork template + bulk generation/export (PDF sheets) for printing.
- Asset registry (master data of applications, sites, lanes, devices, IPs, owners).

### 5.2 Central Web Application (Frontend)
- Mobile-first, industry-grade PWA (works in the browser, installable, usable on low-end phones over 4G).
- Guided troubleshooting UI + embedded **chatbot** (streaming responses, suggested actions, image upload).
- Multilingual UI text (English + Hindi at minimum; extensible).
- Login: lightweight OTP (mobile number) or site-code + PIN for field operators; SSO/credentials for internal staff.
- Ticket creation form with camera capture / gallery upload (1–5 photos, optional short video), auto-attached diagnostic bundle.
- Ticket status tracking for the reporter.
- Admin console: asset registry management, knowledge base management, user/role management, QR generation.
- Operations dashboard: open incidents, health heatmap by site/app/lane, trends, SLA view.

### 5.3 Backend & Integration Layer
- FastAPI-based central backend (REST + WebSocket/SSE for chat streaming).
- **Edge log agent**: lightweight collector installed on each site server/industrial PC that ships application logs, service status, and heartbeats to the central log store (store-and-forward, works over intermittent links).
- Log query service: on-demand retrieval of the last N minutes/hours of logs for a specific asset.
- Health/heartbeat monitoring (device up/down, service up/down, disk, CPU, camera stream status where exposed).
- Ticketing module (create, assign, comment, status workflow, SLA timers, email/WhatsApp/SMS notification hooks) **or** integration with an existing helpdesk if the company already runs one (decision point in Phase 0).

### 5.4 LLM Diagnostic Engine
- LangGraph-based agent: context loading → log retrieval → log analysis → KB retrieval (RAG) → diagnosis → guided-fix dialogue → escalation/ticket tool.
- Knowledge base ingestion pipeline: runbooks, SOPs, past resolved tickets, OEM manuals (PDF/Docx), known-error database; chunking + embeddings + vector store.
- Guardrails: never instruct actions outside operator-safe scope (e.g., no config edits, no electrical work beyond visual checks); confidence thresholds; "escalate" as default when unsure.
- Feedback loop: thumbs up/down on suggestions; resolved-ticket learnings fed back into KB (with human curation).
- Full observability of LLM calls (traces, token cost, latency).

### 5.5 Non-Functional Requirements
- **Security**: HTTPS only, signed QR asset IDs (no enumeration), RBAC, audit logs, log data isolation per client, secrets management, OWASP ASVS L2 alignment.
- **Performance**: chat first-token < 3 s on 4G; page load < 3 s on mid-range Android.
- **Availability**: 99.5% for the central platform; edge agent tolerant to WAN outage (buffer ≥ 72 h of logs locally).
- **Scalability**: designed for 50+ sites, 500+ lanes, 100 concurrent users initially.
- **Data retention**: logs 90 days hot / 1 year archive (configurable per client contract); photos retained with ticket lifetime.
- **Privacy**: ANPR imagery/plate data is regulated client data — the troubleshooting platform accesses *system logs only*, never plate/vehicle payload data, unless explicitly whitelisted.

## 6. Out of Scope (Phase 1)

- Automated remote remediation (auto-restart of services from the platform) — Phase 2 candidate.
- Predictive/preventive failure analytics (ML on telemetry) — Phase 3 candidate.
- Native iOS/Android apps (PWA covers Phase 1).
- Integration with client-side (customer-owned) ticketing systems.
- Voice-based interaction.
- Spare-parts/inventory management.
- Billing/AMC contract management.

## 7. Users & Stakeholders

| Role | Description | Key Interactions |
|------|-------------|------------------|
| Site Operator / Toll Staff | Non-technical user at lane/plaza | Scans QR, chats, follows fix steps, raises ticket with photos |
| Field Technician | Company's on-site engineer | Same as operator + deeper diagnostic view |
| L2/L3 Support Engineer | Central support team | Ticket queue, full logs, diagnosis history |
| Site/Project Manager | Per-site owner | Site dashboard, SLA reports |
| Admin | Platform owner | Asset registry, KB, users, QR generation |
| Client Representative | Highway authority / concessionaire | Read-only incident visibility (optional, configurable) |

## 8. Assumptions

1. Site servers/IPCs can run a lightweight agent and have (at least intermittent) outbound internet to the central platform.
2. Application logs are file-based or syslog-accessible on each system; log formats per application will be documented during Phase 0.
3. Runbooks/SOPs exist or will be authored/curated by SMEs during the project.
4. LLM API usage (cloud) is acceptable for log excerpts and KB content; no regulated payload (plate images, PII) is sent to the LLM. If a client mandates it, a self-hosted model option is a Phase 2 decision.
5. Operators have smartphones with camera and QR scanning capability.

## 9. Constraints

- Poor/intermittent connectivity at remote toll plazas.
- Mixed OS environments on edge (Windows IPCs and Linux servers likely both present).
- Multi-client data isolation obligations.
- Budget for LLM tokens and cloud hosting to be capped and monitored.

## 10. Dependencies

- Access to one pilot site per application type for log-format discovery and UAT.
- SME time for runbook authoring and validation of LLM suggestions.
- Decision on helpdesk build-vs-integrate (existing tool, if any).
- SMS/WhatsApp gateway account for OTP and notifications.

## 11. Risks (Summary)

| Risk | Impact | Mitigation |
|------|--------|-----------|
| LLM gives wrong/unsafe fix steps | High | Operator-safe action whitelist, confidence gating, human-curated KB, mandatory escalation path |
| Log formats undocumented/inconsistent | Medium | Phase 0 log discovery workshop; per-app parsers; graceful "raw log" fallback |
| Site connectivity outages | Medium | Store-and-forward edge agent; QR flow still allows manual ticket with photos even with no logs |
| Low operator adoption | Medium | Dead-simple UX, Hindi support, plaza-level training, QR poster with instructions |
| Token/hosting cost overrun | Low-Med | Prompt caching, small-model routing for classification, per-site budgets, observability |

## 12. High-Level Deliverables

1. Asset registry + QR generation module
2. Central PWA (operator flow + chatbot + ticketing + dashboards + admin)
3. FastAPI backend + LangGraph diagnostic agent + RAG knowledge base
4. Edge log agent + central log store + health monitoring
5. Ticketing workflow with notifications (or helpdesk integration)
6. Deployment (containerised), CI/CD, monitoring, documentation, training material
7. Pilot rollout on 1–2 sites, then phased rollout plan

## 13. Acceptance Criteria (Phase 1 / MVP)

- QR scan on a pilot lane opens the app with correct context pre-selected.
- For 10 seeded known-issue scenarios per application type, the assistant correctly identifies ≥ 8 and provides valid fix guidance.
- Ticket raised from the app lands in the queue with context, chat transcript, log bundle, and ≥ 1 photo.
- Dashboard reflects the incident within 30 seconds.
- Platform passes security checklist (auth, RBAC, HTTPS, signed QR IDs, audit log).
