# AI Field Assistant — Backend

AI-assisted troubleshooting & ticketing platform for manufacturing plant
vision-based inspection systems (e.g. parts inspection machines on a
production line). FastAPI + SQLAlchemy (async) + PostgreSQL/pgvector +
LangGraph, containerized for local dev.

## Build status

This repo is being built milestone by milestone (see project brief). Currently
implemented:

- **Milestone 1**: scaffold, config, docker-compose, DB models matching
  `database-schema.sql`, hand-authored Alembic migration, seed script, model
  smoke tests.
- **Milestone 2**: OTP + JWT auth (`/auth/otp/request`, `/auth/otp/verify`)
  and staff email/password login (`/auth/login`), refresh-token rotation
  (`/auth/refresh`), logout (`/auth/logout`), `/auth/me`.
- **Milestone 3**: admin CRUD for companies/plants/lines/users + plant access
  (`/admin/...`, admin role only), machine registry CRUD and `.xlsx` bulk
  import (`/assets/machines...`), QR token issuance/revocation, public
  token resolution, and sticker PDF export (`/qr/...`, `/a/{token}`).

Everything else (uploads, health/heartbeats, KB ingestion, the LangGraph
agent, tickets/SLA, dashboard) is stubbed as empty routers so the app boots
cleanly, and lands in later milestones.

## Prerequisites

- Docker + Docker Compose v2
- A `.env` file (copy `.env.example` and fill in real secrets — at minimum
  `OPENAI_API_KEY` once you reach the agent milestone)

## Quickstart

```bash
cp .env.example .env   # then edit .env with real secrets

make up                # docker compose up --build
                        # boots postgres(pgvector), redis, minio (+ bucket init),
                        # loki, langfuse (+ its own postgres), api, worker.
                        # The api container runs `alembic upgrade head` on
                        # startup, then serves uvicorn with --reload.
```

Once containers are healthy:

- API: http://localhost:8000 — interactive docs at http://localhost:8000/docs
- MinIO console: http://localhost:9001 (minioadmin / minioadmin)
- Langfuse UI: http://localhost:3000
- Loki: http://localhost:3100

Seed demo data (1 company, 2 plants, 6 lines, 10 visual-inspection machines
with QR tokens, 4 users — one per key role, known_errors for the machine
type):

```bash
make seed
```

Run tests (spins up a throwaway `troubleshoot_test` database, runs the real
Alembic migration against it, then tears it down):

```bash
make test
```

## Other commands

```bash
make logs        # tail api + worker logs
make shell       # shell into the api container
make migrate     # alembic upgrade head (usually automatic on `make up`)
make revision m="add foo column"   # autogenerate a new migration (post-M1 only)
make lint        # ruff check
make fmt         # ruff format
make typecheck   # mypy
```

## Project layout

```
app/
  main.py                # FastAPI app factory, routers, middleware
  config.py               # pydantic-settings, all env vars
  logging.py               # structured JSON logging + request-id context
  core/
    security.py             # password/OTP hashing, JWT + refresh-token issuance
  db/
    base.py / engine.py / session.py / enums.py / pg_types.py
    models/                # SQLAlchemy models, one module per domain
    seed.py                 # `make seed` entrypoint
    alembic/                # migrations (0001_initial hand-authored from
                             # database-schema.sql — keep both in sync)
  api/
    deps.py                 # get_current_user, require_roles
    routes_*.py              # routers — stubs until their milestone
                             # (auth, admin, assets, qr are live)
  schemas/
    auth.py / admin.py / assets.py / qr.py   # Pydantic request/response models
  agent/                   # LangGraph diagnostic agent (Milestone 7)
  services/
    otp.py                   # OTP request/verify/rate-limit (Milestone 2)
    qr.py                    # QR PNG + sticker PDF generation (Milestone 3)
                             # loki_client, storage, notifications, kb_ingest: later
  workers/                 # ARQ background jobs
  tests/
    conftest.py             # test-DB lifecycle fixtures + shared client/admin_headers
    test_models_smoke.py     # full model round-trip against real Postgres
    test_auth.py / test_admin.py / test_assets.py / test_qr.py
                             # API-level tests (httpx ASGITransport)
    fixtures/logs/           # canned per-machine_type log samples for LOKI_FAKE mode
docker-compose.yml
Dockerfile
database-schema.sql        # source of truth — models/migration must match it
```

## Notes on the schema

- `database-schema.sql` is the source of truth. The Alembic migration
  (`app/db/alembic/versions/0001_initial.py`) reproduces it exactly via raw
  SQL rather than autogenerate, so it captures the `updated_at` triggers, the
  ticket-number sequence/trigger, and the pgvector HNSW index. If the schema
  file changes, update the migration (and models) to match.
- `kb_chunks.embedding` is `vector(1024)`. We use OpenAI
  `text-embedding-3-small` with `dimensions=1024` to match — see
  `EMBEDDING_MODEL` / `EMBEDDING_DIM` in `.env.example`.
