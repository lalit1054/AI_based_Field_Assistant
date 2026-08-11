# Claude Code Prompt — Backend

> How to use: create an empty folder (e.g. `troubleshoot-backend/`), place `database-schema.sql` inside it, open Claude Code in that folder, and paste the prompt below. Work feature-by-feature — after the scaffold is built, drive each subsequent milestone as its own follow-up prompt (they are listed at the end).

---

## MASTER PROMPT (paste into Claude Code)

You are building the backend for an **AI-assisted field troubleshooting & ticketing platform** for Intelligent Traffic Systems (ANPR, AVC, SVDS, MLFF) deployed across multiple client sites and lanes. Field operators scan a QR sticker on a faulty device, which opens a web app where an LLM agent reads that asset's logs, diagnoses the issue, guides the operator through safe fix steps, and raises a ticket with photo proof if unresolved.

### Tech stack (do not substitute)
- Python 3.10, **FastAPI**, Uvicorn
- **SQLAlchemy 2.x (async)** + asyncpg + Alembic migrations
- **PostgreSQL 16 with pgvector** — the complete schema is provided in `database-schema.sql` in this folder. Treat it as the source of truth: generate SQLAlchemy models that match it exactly (same table/column names, enums, constraints). Create the initial Alembic migration from this schema.
- **LangGraph + LangChain** for the diagnostic agent (Python)
- **Openai** via `langchain-openapi` (`init_chat_model`), model names from env vars so we can swap
- **Redis** for rate limiting + task queue broker; **ARQ** for background jobs
- **MinIO** (S3-compatible) via `aioboto3` for photos/log bundles/KB source files, using presigned URLs
- **Langfuse** (self-hosted) for LLM tracing — wrap all agent runs
- Pydantic v2 + pydantic-settings for config; ruff + mypy; pytest + httpx + pytest-asyncio for tests
- Docker + docker-compose for local dev

### Project structure
```
app/
  main.py                # FastAPI app factory, routers, middleware
  config.py              # pydantic-settings, all env vars
  db/                    # engine, session, models/, alembic/
  api/
    routes_auth.py       # OTP + JWT
    routes_assets.py     # registry CRUD, QR resolution
    routes_qr.py         # token generation, sticker PDF export
    routes_chat.py       # session lifecycle + SSE stream endpoint
    routes_tickets.py    # ticket CRUD, comments, status workflow
    routes_uploads.py    # presigned upload/download
    routes_health.py     # heartbeat ingest, asset health
    routes_kb.py         # KB document upload + ingestion trigger
    routes_dashboard.py  # aggregate stats
    routes_admin.py      # users, sites, lanes, clients
  agent/
    graph.py             # LangGraph graph definition
    nodes.py             # node implementations
    tools.py             # get_logs, get_health, kb_search, create_ticket
    policy.py            # operator-safe action whitelist check
    prompts.py           # all system prompts, versioned constants
  services/              # loki_client, storage, otp, notifications, qr, kb_ingest
  workers/               # ARQ tasks: kb ingestion, notifications, sla timers
  tests/
docker-compose.yml       # postgres(pgvector), redis, minio, loki, langfuse
Dockerfile
.env.example
```

### Core requirements

**1. Auth**
- `POST /auth/otp/request` → sends OTP (in dev: log to console, pluggable MSG91 provider interface). Rate-limit 3/phone/10min via Redis. Store only `code_hash`.
- `POST /auth/otp/verify` → JWT access (30 min) + refresh token (stored hashed in `refresh_tokens`).
- `POST /auth/login` (email+password) for staff roles. `POST /auth/refresh`.
- RBAC dependency: roles from `user_role` enum. Operators/site managers restricted to sites in `user_site_access`; `admin` bypasses. Enforce at the query level, not just route level.

**2. Asset registry & QR**
- CRUD for clients/sites/lanes/assets (admin only). Bulk import assets from an uploaded Excel/CSV.
- `POST /assets/{id}/qr` → generates a random 26-char url-safe token in `qr_tokens` (revoke old ones optionally).
- `GET /a/{token}` (public) → resolves token → returns asset context `{app_type, site, lane, asset_name, health_summary}`; 404 for unknown/revoked tokens; audit-log every scan with IP. Never expose sequential IDs.
- `POST /qr/sheet` → given asset IDs, generate a printable A4 PDF of QR stickers (segno + reportlab), each labelled with site code / lane / app type, uploaded to MinIO, return presigned URL.

**3. Logs & health**
- `services/loki_client.py`: async client querying Grafana Loki (LogQL) by the asset's `log_labels` for a time window; returns parsed entries. Add `LOKI_FAKE=true` dev mode that serves canned log fixtures per app_type from `tests/fixtures/logs/` so the whole system works before any real site is connected.
- `POST /health/heartbeat` (agent-key auth via `X-Agent-Key` per site): upserts `asset_health`, appends to `heartbeats`. A periodic ARQ job marks assets offline if no heartbeat for 3 minutes.
- `GET /assets/{id}/health` for the frontend health card.

**4. LangGraph diagnostic agent** (the heart of the system)
Build a graph with these nodes, using Postgres checkpointing (`langgraph-checkpoint-postgres`) keyed by `chat_sessions.langgraph_thread_id`:
1. `load_context` — asset metadata, last 5 tickets for this asset, current health.
2. `triage` — SMALL model (env `TRIAGE_MODEL`) classifies complaint into `issue_category`; store on session.
3. `fetch_evidence` — tools: `get_logs(window=30m)`, `get_health()`. Pre-process logs deterministically: drop duplicates, keep WARN/ERROR + 5 lines context, run `known_errors.error_signature` regexes and tag hits.
4. `kb_retrieve` — pgvector cosine search over `kb_chunks`, filtered by `app_type` (+ global docs), top 6.
5. `diagnose_and_guide` — MAIN model (env `DIAGNOSIS_MODEL`). Produces: plain-language diagnosis + numbered operator-safe steps + one question at a time to walk the user through checks. Must respond in the user's `language` (en/hi).
6. `policy_check` — validate suggested actions against `agent/policy.py` whitelist (power-cycle named device, check cable/LED/network light, clean camera glass, verify SIM/router, note error text on screen). If a suggestion falls outside the whitelist → rewrite to escalate. This node is deterministic code + a cheap model call, not trust-the-main-model.
7. `resolve_or_escalate` — if user confirms fixed → mark session `resolved_self`. If user gives up or agent confidence is low → call `create_ticket` tool: auto-fill title/category/priority/diagnosis_summary, link session, attach a log-bundle snapshot (write fetched logs as a .txt to MinIO and create an `attachments` row), return ticket number + SLA due time.
- System prompt rules in `prompts.py`: never invent log content; never suggest configuration changes, electrical work, or software edits; if evidence is insufficient say so and escalate; keep answers under 150 words per turn; use simple language.
- Trace every run with Langfuse (session_id as trace id, record token cost into `chat_sessions.token_cost_usd`).

**5. Chat API**
- `POST /chat/sessions` (body: qr token or asset_id) → creates session, runs `load_context`, returns session + greeting.
- `POST /chat/sessions/{id}/messages` → user message; respond via **SSE** (`text/event-stream`) streaming the agent's reply token-by-token, with structured events: `token`, `tool_start`, `tool_end`, `suggested_actions` (chips like "Yes, LED is green"), `done`. Persist all messages to `chat_messages`.
- `POST /chat/sessions/{id}/rate`, `POST /chat/sessions/{id}/close`.
- Image upload inside chat: presigned upload then `POST /chat/sessions/{id}/attachments` registering the object.

**6. Tickets**
- CRUD honouring RBAC (reporter sees own; support sees all; client_viewer read-only per client).
- Status transitions validated (new→assigned→in_progress→resolved→closed, reopen allowed from resolved/closed); every transition writes `ticket_status_history`; SLA due times computed from `sla_policies` on create; ARQ job flags breaches and queues notifications.
- Comments (internal flag hidden from operator/client roles). Attachment listing with presigned GET URLs (10 min expiry).
- Notifications on create/assign/breach via a provider interface (dev: console; prod: MSG91 WhatsApp/SMS + SMTP email). Write rows to `notifications`.

**7. Knowledge base**
- `POST /kb/documents` (admin): upload PDF/DOCX to MinIO → ARQ job parses (pymupdf for PDF, python-docx for DOCX), chunks ~800 tokens with 100 overlap, embeds (env `EMBEDDING_MODEL`, provider-agnostic wrapper; dev mode: deterministic fake embeddings so tests run offline), inserts `kb_chunks`.
- CRUD for `known_errors` (admin/support).

**8. Dashboard**
- `GET /dashboard/summary`: open tickets by status/priority, incidents by site (heatmap data), top recurring categories per app_type (30d), assets offline now, avg resolution time, self-fix rate.

### Non-negotiables
- Every route has Pydantic request/response schemas; OpenAPI must be clean (frontend will be generated from it).
- Global exception handler, request-id middleware, structured JSON logging.
- Audit-log: QR scans, logins, ticket create/status change, KB uploads, admin CRUD.
- Rate limiting on all public/auth endpoints.
- `docker-compose up` must bring up everything; `make seed` creates 1 client, 2 sites, 6 lanes, 10 assets (mixed app types), QR tokens, 4 users (one per key role), 3 known_errors per app_type, and fake log fixtures — so the frontend team can develop immediately.
- Tests: auth flow, QR resolution, RBAC isolation, ticket workflow + SLA calc, agent graph unit tests with mocked LLM, one end-to-end chat test using `LOKI_FAKE` + fake LLM.

### Build order (implement in this order, confirm each milestone compiles and tests pass before moving on)
1. Scaffold + config + docker-compose + DB models from `database-schema.sql` + Alembic + seed script
2. Auth (OTP + JWT + RBAC) 
3. Asset registry + QR generation + public QR resolution + sticker PDF
4. MinIO presigned uploads + attachments
5. Loki client (with fake mode) + heartbeat ingest + health endpoints
6. KB ingestion pipeline + vector search service
7. LangGraph agent + tools + policy check + SSE chat endpoints
8. Tickets + SLA + notifications + status history
9. Dashboard aggregates
10. Hardening: rate limits, audit coverage, test gaps, README with run instructions

Start with milestone 1 now. Show me the project tree and docker-compose before writing all the code.

---

## Follow-up prompts to use per milestone
- "Milestone 2: implement auth exactly as specified. Then write tests covering OTP rate limiting, expiry, JWT refresh, and RBAC site isolation."
- "Milestone 7: build the LangGraph agent. First show me the graph diagram (nodes/edges) and the state schema as a Pydantic model, get my approval, then implement."
- "Run all tests, fix failures, then update README with setup + seed + demo walkthrough."
