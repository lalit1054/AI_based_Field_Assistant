# Detailed Plan Document

## AI-Assisted Field Troubleshooting & Ticketing Platform (QR-Based)

| | |
|---|---|
| **Document Version** | 1.0 (Draft) |
| **Date** | 08 July 2026 |
| **Companion Document** | Scope Document v1.0 |

---

## 1. Solution Architecture

### 1.1 High-Level Components

```
 [QR Sticker on Asset]
        │  scan (phone camera)
        ▼
 https://support.company.com/a/<signed-asset-id>
        │
        ▼
┌──────────────────────────────┐
│  Frontend PWA (React)        │  operator flow, chatbot, ticket + photos,
│  mobile-first, installable   │  dashboards, admin console
└──────────────┬───────────────┘
               │ REST + SSE/WebSocket
               ▼
┌──────────────────────────────┐        ┌───────────────────────┐
│  FastAPI Backend             │◄──────►│ PostgreSQL (assets,   │
│  auth, assets, tickets,      │        │ tickets, users, chat) │
│  chat orchestration API      │        └───────────────────────┘
└──────┬──────────┬────────────┘
       │          │                     ┌───────────────────────┐
       │          └────────────────────►│ Object Storage (S3/   │
       │                                │ MinIO): photos, log   │
       │                                │ bundles, KB docs      │
       ▼                                └───────────────────────┘
┌──────────────────────────────┐
│  LangGraph Diagnostic Agent  │──► LLM API (Claude / GPT)
│  tools: get_logs, get_health,│──► Vector DB (RAG over runbooks,
│  kb_search, create_ticket,   │        SOPs, known errors)
│  escalate                    │──► Langfuse (traces/cost)
└──────────────┬───────────────┘
               │ query logs/health
               ▼
┌──────────────────────────────┐
│  Log & Health Platform       │  Grafana Loki (logs) +
│  (central)                   │  Prometheus/heartbeat API
└──────────────▲───────────────┘
               │ push (store-and-forward)
┌──────────────┴───────────────┐
│  EDGE (each site server/IPC) │  Grafana Alloy / Fluent Bit agent:
│  ANPR/AVC/SVDS/MLFF hosts    │  tails app logs, service status,
│  Windows + Linux             │  heartbeat; buffers during WAN loss
└──────────────────────────────┘
```

### 1.2 Key Design Decisions

**D1 — QR encodes the asset, not just the app URL.**
Each sticker's URL contains a signed, non-guessable asset token (e.g., `/a/9f3k...`), mapping to `{app_type, site, lane, host}` in the asset registry. Benefits: zero typing for the operator, no wrong-lane reports, and no ID enumeration by outsiders. The manual dropdown flow (App → Site → Lane) remains as fallback for damaged stickers.

**D2 — Push-based log collection (edge agent), not remote pull.**
Toll sites sit behind NAT/firewalls with flaky links. A lightweight agent on each host tails log files/Windows Event Log, adds labels (`site`, `lane`, `app`, `host`), buffers to disk during outages, and pushes to central Loki. The diagnostic agent then queries Loki with those labels — no inbound access to sites needed. Heartbeat gaps themselves become a signal ("device/site offline").

**D3 — LLM works on excerpts + structure, not raw log dumps.**
The agent pipeline: (1) pull last 15–60 min of logs for the asset; (2) deterministic pre-processing — dedupe, severity filter, known-pattern regex tagging; (3) send the distilled excerpt + health snapshot + top-k KB chunks to the LLM. This keeps token cost low, latency acceptable, and avoids sending sensitive payload data.

**D4 — Operator-safe action policy.**
The agent may only suggest actions from a whitelisted taxonomy per app type (power-cycle device X, check cable/LED, verify network light, restart service via provided one-click script if permitted, clean camera glass, etc.). Anything else → escalate + ticket. Enforced via system prompt + a post-generation policy check node in the graph.

**D5 — Build a focused ticketing module in-house (Phase 1), keep an integration adapter interface.**
The ticket lifecycle needed (New → Assigned → In Progress → Resolved → Closed, SLA timers, comments, attachments, notifications) is small enough to own, keeps UX unified inside the PWA, and avoids per-agent helpdesk licensing. If the company later standardises on Jira Service Management/Freshdesk/Zammad, an adapter syncs tickets outward.

### 1.3 LangGraph Agent Design

Nodes (roughly):

1. **load_context** — resolve asset token → app/site/lane/host metadata, recent ticket history for this asset.
2. **triage** — fast/cheap model classifies the user's complaint into a category (connectivity / app crash / API error / camera-image issue / data mismatch / unknown).
3. **fetch_evidence** — tool calls: `get_logs(asset, window)`, `get_health(asset)`, `get_heartbeat(site)`.
4. **analyse** — main model reasons over distilled evidence; regex/known-error tagger output included.
5. **kb_retrieve** — vector search filtered by `app_type` (+ category) over runbooks/known errors/resolved tickets.
6. **diagnose_and_guide** — produce plain-language diagnosis + numbered operator-safe steps; interactive loop ("Did the LED turn green?").
7. **policy_check** — validates suggested actions against the whitelist; rewrites or escalates on violation.
8. **resolve_or_escalate** — on failure/uncertainty: `create_ticket` tool with auto-filled context, transcript, log bundle snapshot, photos; return ticket number + expected SLA.

Cross-cutting: checkpointing (Postgres) so a session survives page refresh; Langfuse tracing on every run; per-session token budget.

### 1.4 Data Model (Core Entities)

`clients` → `sites` → `lanes` → `assets` (app instance on host, type ∈ {ANPR, AVC, SVDS, MLFF}) → `qr_tokens`;
`users`, `roles`; `chat_sessions`, `chat_messages`; `tickets`, `ticket_comments`, `ticket_attachments`, `sla_policies`;
`kb_documents`, `kb_chunks` (vector), `known_errors`; `heartbeats`, `health_snapshots`; `audit_log`.

---

## 2. Recommended Tools & Libraries (Research Summary)

### 2.1 Frontend (React PWA)

| Purpose | Recommendation | Why / Alternatives |
|---|---|---|
| Framework | **React 19 + Vite + TypeScript** | Fast builds, simple SPA/PWA deployment behind FastAPI or CDN. Next.js only if you later need SSR/SEO (you don't for an internal tool). |
| UI components | **shadcn/ui + Tailwind CSS** | Industry-standard look, fully ownable code, great with Claude Code generation. Alt: MUI, Ant Design. |
| **Chatbot UI** | **assistant-ui (`@assistant-ui/react`)** | Purpose-built React chat library with a **first-party LangGraph runtime adapter** (`useLangGraphRuntime`), streaming, markdown, attachments, tool-call rendering (generative UI), human-in-the-loop — exactly your stack. Alt: Vercel AI Elements, CopilotKit, @llamaindex/chat-ui, or hand-rolled with `ai` SDK. |
| Server state | **TanStack Query** | Caching/polling for tickets, dashboards. |
| Client state | **Zustand** | Lightweight; enough for session/UI state. |
| Forms + validation | **React Hook Form + Zod** | Ticket forms, admin CRUD. |
| Routing | **React Router v7** | Deep links from QR (`/a/:token`). |
| PWA | **vite-plugin-pwa (Workbox)** | Installable, offline shell, camera access via `<input capture>` / `getUserMedia`. |
| Photo handling | **browser-image-compression** | Compress 12 MP photos client-side before upload (critical on 4G). |
| QR scan fallback (in-app) | **@zxing/browser** or html5-qrcode | If you also want scanning inside the app. |
| Charts/dashboard | **Recharts** (or ECharts for heatmaps) | Incident trends, site health heatmap. |
| i18n | **react-i18next** | English/Hindi. |
| Tables | **TanStack Table** | Ticket queues, asset registry. |

### 2.2 Backend (Python)

| Purpose | Recommendation | Why / Alternatives |
|---|---|---|
| API framework | **FastAPI** (+ Uvicorn/Gunicorn) | Your existing skill; async, SSE/WebSocket support. |
| ORM / migrations | **SQLAlchemy 2 + Alembic** | Mature, async support. Alt: SQLModel. |
| Database | **PostgreSQL 16** | Relational core + `pgvector` extension (see RAG). |
| Auth | **fastapi-users** or custom JWT + **OTP via MSG91/Twilio**; **Keycloak** if you need enterprise SSO later | Operators: phone OTP; staff: username/password or SSO. |
| Background jobs | **Celery + Redis** (or ARQ/Dramatiq for lighter footprint) | KB ingestion, notifications, log-bundle snapshots, SLA timers. |
| Object storage | **MinIO** (self-hosted, S3 API) or AWS S3 | Photos, log bundles, KB PDFs. Use presigned upload URLs. |
| File/PDF parsing (KB ingest) | **Docling** or **unstructured** + PyMuPDF | Runbooks/OEM manuals → clean chunks. |
| QR generation | **segno** (or `qrcode`) + ReportLab/WeasyPrint for printable sticker sheets | Bulk PDF generation with asset labels. |
| Validation/config | **Pydantic v2 + pydantic-settings** | Already in FastAPI ecosystem. |
| Notifications | **MSG91 / Gupshup (WhatsApp Business API, India-friendly), smtplib/Resend for email** | Ticket alerts to engineers. |
| Rate limiting / security | **slowapi**, `python-jose`, HTTPS via Traefik/Caddy | Protect public QR endpoints. |

### 2.3 LLM / Agent Layer

| Purpose | Recommendation | Why / Alternatives |
|---|---|---|
| Orchestration | **LangGraph** (Python) | Your skill; checkpointing, tool nodes, human-in-the-loop; pairs with assistant-ui on the frontend. |
| LLM | **Claude Sonnet** class model for diagnosis; **Haiku/small model** for triage classification | Cost routing: cheap model for classification, strong model for reasoning. Keep provider-agnostic via LangChain `init_chat_model`. |
| Embeddings | **voyage-3.5 / text-embedding-3-large / bge-m3 (self-host)** | bge-m3 if you want zero external calls for KB. |
| Vector store | **pgvector** (start) → **Qdrant** (if scale demands) | pgvector keeps one database to operate; Qdrant when KB grows large or you need advanced filtering performance. |
| Observability | **Langfuse (self-hostable)** | Traces, cost per session, prompt versioning, user feedback capture. Alt: LangSmith (SaaS). |
| Evals | **Langfuse datasets + pytest harness**; promptfoo for prompt regression | Seeded known-issue scenarios as regression suite. |
| Guardrails | Whitelist policy node + structured outputs (Pydantic) ; optionally **NeMo Guardrails** | Keep it simple first. |

### 2.4 Logs, Health & Monitoring

| Purpose | Recommendation | Why / Alternatives |
|---|---|---|
| Edge log shipper | **Grafana Alloy** or **Fluent Bit** | Tiny footprint, Windows + Linux, tail files + Windows Event Log, disk buffering (store-and-forward), label injection (site/lane/app). |
| Central log store | **Grafana Loki** | Label-based queries map perfectly to asset labels; cheap storage (object store backend); simple LogQL API the agent can call. Alt: OpenSearch (heavier, full-text). |
| Metrics/heartbeat | **Prometheus + Alloy** (node/windows exporters) or a simple heartbeat POST endpoint in FastAPI | Device/service up-down, disk, CPU. |
| Dashboards (internal ops) | **Grafana** | Ops team view; PWA dashboard covers business view. |
| Uptime/alerting | **Grafana Alerting** or Uptime Kuma | Site offline alerts even before an operator scans QR. |

### 2.5 DevOps & Delivery

| Purpose | Recommendation |
|---|---|
| Containerisation | Docker + Docker Compose (Phase 1); K3s/Kubernetes only if multi-node scale demands |
| Reverse proxy / TLS | Traefik or Caddy (auto-TLS) |
| CI/CD | GitHub Actions (build, test, image push, deploy) |
| IaC (if cloud) | Terraform |
| Error tracking | Sentry (frontend + backend) |
| Secrets | Docker secrets / SOPS; Vault if it grows |
| Testing | pytest + httpx (API), Playwright (E2E for PWA), Locust (load) |

---

## 3. Work Breakdown & Phased Plan

> Durations assume 1 full-stack developer (you) + Claude Code assistance + part-time SME for runbooks. Adjust ±30% for parallel duties.

### Phase 0 — Discovery & Foundations (2–3 weeks)
- Inventory pilot assets: apps, hosts, OS, log file paths/formats for ANPR, AVC, SVDS, MLFF.
- Collect/author top 10 known issues + fix runbooks per application type (SME workshops).
- Decide: helpdesk build vs integrate; cloud vs on-prem hosting; LLM provider & data policy.
- Finalise asset ID scheme, QR URL format & signing, sticker artwork.
- Repo setup, CI skeleton, environments (dev/stage/prod), coding standards.
- **Exit criteria:** signed-off log inventory, runbook set v1, architecture sign-off.

### Phase 1 — MVP (6–8 weeks)

**Sprint 1–2: Core platform**
- Asset registry (CRUD + import from Excel), QR token generation + printable PDF sheets.
- Auth (OTP for operators, credentials for staff), RBAC.
- PWA shell: QR landing page (`/a/:token`) with context confirmation; manual App→Site→Lane fallback.

**Sprint 2–3: Logs & health pipeline**
- Edge agent config templates (Alloy/Fluent Bit) for Windows + Linux; deploy to pilot site.
- Central Loki + heartbeat endpoint; asset-scoped log query API in FastAPI.
- Basic health status card in the PWA ("device last seen 2 min ago").

**Sprint 3–4: Diagnostic agent + chatbot**
- KB ingestion pipeline (runbooks → chunks → pgvector).
- LangGraph agent (nodes per §1.3) with tools; SSE streaming endpoint.
- assistant-ui chat integration with LangGraph runtime; suggested-action chips; photo upload in chat.
- Langfuse tracing + seeded-scenario eval harness (10 scenarios/app type).

**Sprint 4–5: Ticketing + dashboard**
- Ticket module: create (auto-filled from session), lifecycle, comments, attachments, SLA timers.
- Notifications (WhatsApp/SMS/email) to assigned engineer.
- Reporter "my tickets" view; ops dashboard (open incidents, site heatmap, trends).
- Admin console: KB upload/curation, users, assets.

**Sprint 5–6: Hardening & pilot**
- Security pass (signed tokens, rate limits, audit log, pen-test checklist), load test, offline/poor-network testing.
- Pilot deployment at 1–2 sites; operator training (poster + 2-min video); feedback loop.
- **Exit criteria:** MVP acceptance criteria from Scope §13 met at pilot sites.

### Phase 2 — Rollout & Assist Automation (4–6 weeks)
- Rollout to remaining sites (agent deployment playbook, bulk QR printing).
- One-click safe remediations (e.g., controlled service restart via agent command channel, with approval + audit).
- Resolved-ticket → KB learning loop (curated).
- Client read-only portal (optional), SLA reports, CSV/Excel exports.
- Cost optimisation: prompt caching, small-model routing, per-site budgets.

### Phase 3 — Intelligence (ongoing)
- Proactive alerts: heartbeat/log-pattern detection opens a draft incident *before* anyone scans.
- Trend analytics: recurring-fault ranking per device model/site, MTBF reports.
- Optional self-hosted LLM path for strict clients; predictive maintenance exploration.

### Indicative Timeline

```
Weeks:  1  2  3 | 4  5  6  7  8  9 10 11 | 12 13 14 15 16 17
Phase0: ██████
Phase1:          ██████████████████████
Pilot:                             ▓▓▓▓
Phase2:                                     ████████████████
```

---

## 4. Team & Effort (Lean Setup)

| Role | Allocation | Notes |
|---|---|---|
| Full-stack dev (you) | 100% | Backend, agent, frontend with Claude Code |
| SME (support engineer) | 20–30% | Runbooks, scenario validation, UAT |
| Field tech | Ad hoc | Edge agent installs, sticker placement |
| Reviewer/PM | 10% | Sign-offs, client coordination |

---

## 5. Cost Considerations (Order of Magnitude)

- **LLM tokens:** with excerpt-based prompts + caching + small-model triage, expect roughly $0.01–0.05 per troubleshooting session; budget alerting via Langfuse.
- **Hosting:** single 8 vCPU/32 GB VM (or 2 smaller) runs Postgres, Loki, MinIO, backend, Langfuse comfortably at Phase-1 scale.
- **Messaging:** OTP + WhatsApp notification costs per message (MSG91/Gupshup rate cards).
- **Zero-license stack:** everything above is OSS except the LLM API and messaging gateway.

---

## 6. Security & Compliance Checklist

- Signed, random QR asset tokens; tokens revocable/rotatable per asset.
- OTP login even for QR flow (scan ≠ authentication); throttling on OTP endpoints.
- RBAC: operator sees only own site's assets/tickets; client isolation at query level.
- No ANPR payload (plate images/numbers) leaves site systems; agent collects *application logs only*; log-scrubbing filters for accidental PII patterns.
- Presigned, size- and type-limited photo uploads; EXIF GPS stripped or retained per policy.
- Full audit trail: who scanned, what the agent advised, what actions were suggested/taken.
- TLS everywhere; secrets outside images; dependency scanning in CI.

---

## 7. Open Questions (to close in Phase 0)

1. Exact log locations/formats per application and OS mix at sites?
2. Existing helpdesk tool in the company, if any — integrate or replace?
3. Cloud hosting allowed by client contracts, or on-prem/company DC required?
4. Which languages beyond English/Hindi?
5. Is a controlled command channel (remote restart) acceptable to clients in Phase 2?
6. Who owns KB curation after go-live (named SME)?
