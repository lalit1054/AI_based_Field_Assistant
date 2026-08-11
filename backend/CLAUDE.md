# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Backend for an AI-assisted troubleshooting & ticketing platform for manufacturing
plant vision-based inspection systems (e.g. parts inspection machines on a
production line). FastAPI + SQLAlchemy (async) + PostgreSQL/pgvector + LangGraph,
containerized for local dev via docker-compose.

Domain hierarchy: a **Company** (e.g. JBM) owns one or more **Plants** (e.g. "3xo
Nashik"), each Plant has **Lines** (e.g. "Line 1"), and **Machines** (e.g. "VI 12
parts inspection system") sit on a Line or directly on a Plant. Every Machine
currently has `machine_type = VISUAL_INSPECTION` — the enum has one member today,
kept as an enum because more machine types are expected later.

The repo is being built milestone by milestone. **Milestones 1–3** are implemented;
every other route module in `app/api/` is a stub router so the app boots cleanly. Check
a route module's docstring before assuming it has real logic to build on — each names
the milestone it's implemented in:

| Milestone | Scope | Status |
|---|---|---|
| 1 | Scaffold, config, docker-compose, DB models matching `database-schema.sql`, hand-authored Alembic migration, seed script, model smoke tests | **Done** |
| 2 | `routes_auth` — phone + JWT auth (no OTP), staff login | **Done** |
| 3 | `routes_admin`, `routes_assets` (registry), `routes_qr` — company/plant/line/machine CRUD, bulk import, QR generation | **Done** |
| 4 | `routes_uploads` — presigned upload/download for MinIO attachments | **Done** |
| 5 | `routes_health` — agent-key heartbeat ingest, machine health card, offline sweep | **Done** |
| 6 | `routes_kb` — KB document upload/ingestion (fake embeddings), known_errors CRUD | **Done (bounded — see below)** |
| 7 | `routes_chat` — chat session/message persistence, canned-reply placeholder | **Done (bounded — no LangGraph agent yet, see below)** |
| 8 | `routes_tickets` — ticket CRUD, comments, status workflow, SLA | **Done** |
| 9 | `routes_dashboard` — aggregate dashboard stats | **Done** |

`app/services/` now has `qr.py` (M3), `storage.py` (M4, MinIO presign),
`loki_client.py` (M5, log fetch with `LOKI_FAKE` canned-fixture fallback),
`kb_ingest.py` (M6, chunking + `EMBEDDING_FAKE` hash-based fake vectors),
`canned_reply.py` (M7, keyword-matched placeholder reply). `notifications`
still doesn't exist — nothing yet triggers SLA/status notifications.

### Milestones 6 & 7 — deliberately bounded scope

Both shipped enough to unblock the frontend, but stopped short of the "real"
AI behavior on purpose (matches the product decision at the time — revisit
when the LangGraph agent work is scoped):
- **KB (M6)**: document chunking + embedding pipeline is real, but embeddings
  are a deterministic SHA-256-derived fake vector whenever `EMBEDDING_FAKE=true`
  (the default) — no OpenAI call, no real semantic retrieval yet. `known_errors`
  CRUD is fully real; `engineer_fix_steps` is masked to `null` in API responses
  for the `operator` role.
- **Chat (M7)**: `ChatSession`/`ChatMessage` persistence is real (`POST
  /chat/sessions`, `POST/GET /chat/sessions/{id}/messages`), but there's no
  LangGraph agent and no SSE streaming — `POST .../messages` synchronously
  returns a canned, keyword-matched assistant reply
  (`app/services/canned_reply.py`, ported from the frontend's old
  `mockAssistant.ts` so behavior didn't regress). `app/agent/` still doesn't
  exist.

### Milestone 5 — health

Machines authenticate heartbeat ingest with a **shared per-plant key**, not a
JWT — `require_agent_heartbeat` (`app/api/deps.py`) checks the `x-plant-code`/
`x-agent-key` headers against `settings.agent_heartbeat_key_map`, and the
route double-checks the target machine actually belongs to that plant code.
`POST /health/heartbeat` upserts the single-row-per-machine `machine_health`
table and appends to the time-series `heartbeats` table. A new ARQ cron job
(`mark_stale_machines_offline` in `app/workers/tasks.py`, registered in
`WorkerSettings.cron_jobs`, every 5 minutes) flips `is_online=false` for any
machine whose last heartbeat is older than 5 minutes — there's no
"went offline" push event, so this sweep is what keeps the dashboard's
online/offline counts honest without a heartbeat.

### Milestone 8 — tickets

`POST /tickets` requires a logged-in user (any role) — the QR-landing "report
an issue" flow now does an `/auth/login-phone` call first, so every ticket has
a real `reporter_id` instead of being anonymous. SLA due dates
(`first_response_due_at`/`resolution_due_at`) are computed from the
pre-seeded `sla_policies` row matching the ticket's priority. Access is
scoped: `admin` sees everything, `operator` sees only tickets they reported,
every other role is scoped to plants they hold `user_plant_access` for — this
is the first route module to actually enforce that table (it existed since
M1 but nothing read it before). Status changes write a `ticket_status_history`
row; ticket create/update also write an `audit_log` row.

### Milestone 9 — dashboard

`GET /dashboard/stats` is a handful of grouped-count queries (plants,
machines, `machine_health.is_online` counts, open-ticket count, 5 most recent
tickets) — no new tables, no caching. Accepts an optional `?plant_id=` and
applies the same `user_plant_access` scoping as tickets when the caller isn't
`admin`.

### Milestone 4 — uploads

`app/services/storage.py` wraps plain (sync) `boto3` — presigning is a local
HMAC computation, not a network call, so there's no need for `aioboto3`'s
async client here despite it being the project's chosen S3 SDK elsewhere.
`POST /uploads/presign` validates the target `ticket_id`/`session_id` exists
(exactly one of the two is required, matching the `attachments` table's CHECK
constraint) and returns a presigned PUT URL; `POST /uploads/attachments` is
called by the client *after* the actual upload succeeds, to persist the
`Attachment` row and hand back a presigned GET URL.

### Milestone 2 — auth

- `app/core/security.py` — password hashing (bcrypt via passlib), JWT access-token
  issuance/decoding (PyJWT, HS256), and opaque refresh tokens (`secrets.token_urlsafe`,
  stored as a SHA-256 hash — high-entropy random values don't need a slow salted hash
  like bcrypt).
- `app/api/deps.py` — `get_current_user` (Bearer JWT → `User`, via `app.db.session.get_session`)
  and `require_roles(*roles)`, a dependency factory later milestones should use to gate
  role-restricted endpoints.
- `app/api/routes_auth.py` — `POST /auth/login-phone` (phone only, no OTP/verification
  step; self-registers an `operator` User on first login — field ops have no separate
  signup flow), `POST /auth/login` (staff email+password), `POST /auth/refresh`
  (rotates the refresh token — old one is revoked), `POST /auth/logout` (revokes a
  refresh token), `GET /auth/me`. There used to be an OTP request/verify step here
  (`otp_codes` table, `app/services/otp.py`) — it was removed since phone verification
  isn't required; migration `0002_drop_otp_codes` drops the now-unused table.
- `app/main.py` gained an `HTTPException` handler so 401/403/404/429s use the same
  `{"error": ..., "detail": ...}` envelope as the validation/500 handlers.
- Tests: `app/tests/test_auth.py` drives the real FastAPI app in-process (httpx
  `ASGITransport`) against the Alembic-migrated test database — not just the ORM layer.
  This required two test-infra fixes in `app/tests/conftest.py`, worth knowing about
  before adding more API-level tests:
  - `DATABASE_URL`/`DATABASE_URL_SYNC` env vars are overridden to point at
    `troubleshoot_test` *before* `app.config` (and anything importing it, like
    `app.db.engine`'s module-level connection pool used by the real API routes) is ever
    imported — otherwise the app under test would silently hit the dev database.
  - `pyproject.toml` sets `asyncio_default_fixture_loop_scope`/`asyncio_default_test_loop_scope`
    to `"session"` — `app.db.engine`'s async engine is a singleton bound to whichever
    event loop first opens a connection; pytest-asyncio's default per-test loop would
    make later tests reuse pooled connections from a dead loop and crash.
  - `app/tests/conftest.py` also exposes shared `client` (httpx `ASGITransport` against
    `app.main.app`) and `admin_headers` (creates an admin `User`, logs in, returns an
    `Authorization` header dict) fixtures — reuse these rather than redefining per test
    module; `test_admin.py`/`test_assets.py`/`test_qr.py` all build on them.

### Milestone 3 — registry, bulk import, QR

- `app/api/routes_admin.py` — CRUD for companies/plants/lines/users plus
  grant/revoke/list `user_plant_access`. The whole router requires the `admin` role
  (`dependencies=[Depends(require_roles(UserRole.admin))]` on the `APIRouter` itself) —
  this is back-office management, not exposed to plant-scoped roles yet.
- `app/api/routes_assets.py` — machine CRUD (`/assets/machines`) plus
  `POST /assets/machines/bulk-import` (`.xlsx` via openpyxl: `plant_code`/`name`
  required, `line_number`/`hostname`/`device_model`/`notes` optional; plants and lines
  must already exist — the endpoint doesn't create them; returns
  `{created, errors: [{row, error}]}` rather than failing the whole batch on one bad
  row). Reads (`GET`) only require login; writes require one of
  `WRITE_ROLES = (admin, support_l2, support_l3, plant_manager)` — this write-role set
  is duplicated in `routes_assets.py` and `routes_qr.py` (not shared) since each router
  currently gates a slightly different action; consolidate if a third router needs it.
- `app/api/routes_qr.py` — `POST /qr/machines/{id}/tokens` (issues a new token; by
  default revokes any existing active tokens for that machine — pass
  `revoke_existing=false` to keep old ones live), `GET /qr/machines/{id}/tokens`,
  `POST /qr/tokens/{id}/revoke`, `GET /a/{token}` (**public, no auth** — this is what a
  scanned sticker resolves to; logs an `audit_log` row), `GET
  /qr/machines/{id}/sticker.pdf` and `POST /qr/stickers/export` (bulk, one sticker per
  PDF page) via `app/services/qr.py` (segno for the QR PNG, reportlab for the label
  PDF — `STICKER_SIZE` is 80×50mm, tune there if the physical label size changes).
- `app/core/security.generate_qr_token()` is shared between `routes_qr.py` and
  `app/db/seed.py` — don't reintroduce the inline `secrets.token_urlsafe(...)[:26]`
  that used to live in `seed.py`.

The domain was converted from an Intelligent-Traffic-Systems platform (Client/Site/Lane/
Asset, ANPR/AVC/SVDS/MLFF) to a manufacturing-plant one (Company/Plant/Line/Machine,
single `VISUAL_INSPECTION` machine type). No code uses the old naming anymore.

## Commands

All commands run through Docker Compose (there's no local venv workflow assumed by the
Makefile, though a `.venv` exists for editor tooling/IDE support).

```bash
cp .env.example .env       # first-time setup; fill in secrets (OPENAI_API_KEY etc.)
make up                    # docker compose up --build — postgres/pgvector, redis, minio,
                            # loki, langfuse(+its own postgres), api, worker.
                            # api container runs `alembic upgrade head` then uvicorn --reload.
make down
make logs                  # tail api + worker logs
make shell                 # shell into the api container
make seed                  # python -m app.db.seed — demo data (1 company, 2 plants, 6 lines,
                            # 10 machines w/ QR tokens, 4 users, known_errors for the machine type)
make migrate                # alembic upgrade head (usually automatic on `make up`)
make revision m="add foo"   # alembic revision --autogenerate -m "..." (post-M1 only —
                             # migration 0001 is hand-authored, not autogenerated)
make test                   # spins up a throwaway `troubleshoot_test` db, runs the real
                             # Alembic migration against it, runs pytest, tears it down
make lint                   # ruff check .
make fmt                    # ruff format .
make typecheck               # mypy app
```

Run a single test: `docker compose exec api pytest -v app/tests/test_auth.py::test_name`

API docs at http://localhost:8000/docs once `make up` is healthy. MinIO console at
:9001 (minioadmin/minioadmin), Langfuse UI at :3000, Loki at :3100.

## Architecture

- `app/main.py` — FastAPI app factory (`create_app`). Registers a request-id middleware
  (propagates/generates `x-request-id`), a `RequestValidationError` handler and a
  catch-all exception handler (both return `{"error": ..., "detail": ...}` JSON), and
  every router in `app/api/`.
- `app/config.py` — single `pydantic-settings` `Settings` class, all env vars in one
  place, cached via `get_settings()` (`lru_cache`). Notable feature flags:
  `LOKI_FAKE` and `EMBEDDING_FAKE` (dev/test mode toggles), `notify_provider` =
  `"console"` in dev. `agent_heartbeat_key_map` parses
  `AGENT_HEARTBEAT_KEYS` (`"PLANT_CODE:key,PLANT_CODE2:key2"`) into a dict for
  per-plant heartbeat auth.
- `app/db/` — `base.py`/`engine.py`/`session.py` set up the async SQLAlchemy engine;
  `enums.py` holds Python mirrors of the Postgres enum types (must stay byte-for-byte
  in sync with `database-schema.sql` — wired via `sqlalchemy.Enum(..., create_type=False)`
  since the actual `CREATE TYPE` happens in the migration, not SQLAlchemy DDL).
- `app/db/models/` — one module per domain: `assets` (Company/Plant/Line/Machine/QrToken),
  `users` (User/UserPlantAccess/RefreshToken), `chat` (ChatSession/ChatMessage),
  `tickets` (SlaPolicy/Ticket/TicketComment/TicketStatusHistory), `attachments`, `kb`
  (KbDocument/KbChunk/KnownError), `health` (MachineHealth/Heartbeat), `audit`
  (AuditLog/Notification).
- **`database-schema.sql` is the source of truth for the schema.** The Alembic
  migration `app/db/alembic/versions/0001_initial.py` reproduces it via raw SQL
  (not autogenerate) to capture `updated_at` triggers, the ticket-number
  sequence/trigger, and the pgvector HNSW index. If the schema file changes, update
  both the migration and the SQLAlchemy models to match — they must stay in sync by
  hand, not by regenerating.
- `kb_chunks.embedding` is `vector(1024)` — uses OpenAI `text-embedding-3-small` with
  `dimensions=1024` to match (`EMBEDDING_MODEL`/`EMBEDDING_DIM` in settings).
- `app/api/routes_*.py` — one router module per resource area; import and register
  new routers in `app/main.py`. `routes_auth.py`, `routes_admin.py`, `routes_assets.py`,
  `routes_qr.py` have real logic — see the Milestone 2/3 sections above.
- `app/api/deps.py` — shared FastAPI dependencies: `get_current_user`, `require_roles`.
- `app/core/security.py` — password hashing, JWT + refresh-token issuance, QR token
  generation.
- `app/agent/` — LangGraph diagnostic agent (Milestone 7, not yet built).
- `app/services/` — `qr.py` (Milestone 3, QR PNG + sticker PDF generation);
  `loki_client`, `storage`, `notifications`, `kb_ingest` not yet built.
- `app/schemas/` — Pydantic request/response models, one module per resource area
  (`auth.py`, `admin.py`, `assets.py`, `qr.py`).
- `app/workers/` — ARQ background job definitions (`tasks.py`) and `WorkerSettings`
  (`settings.py`), run via `arq app.workers.settings.WorkerSettings`.
- `app/tests/conftest.py` — owns the test-DB lifecycle (creates `troubleshoot_test`,
  runs the real Alembic migration, tears down after). `app/tests/fixtures/logs/`
  holds canned per-`machine_type` log samples used when `LOKI_FAKE=true`.

## Compose services

`postgres` (pgvector/pgvector:pg16), `redis`, `minio` + `minio-init` (creates the
`attachments`, `log-bundles`, `kb-sources`, `qr-sheets` buckets on startup), `loki`,
`langfuse` + its own `langfuse-db`, `api`, `worker`. The `api` and `worker` containers
both mount `./:/code` for live reload during dev.
