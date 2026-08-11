# AI Field Assistant

AI-assisted troubleshooting & ticketing platform for Intelligent Traffic System (ITS) deployments — ANPR, AVC, SVDS, MLFF — across multiple client sites and lanes.

Every deployed unit carries a QR sticker. Scanning it opens a mobile-first web app where an LLM-based diagnostic assistant reads the system's recent logs/health/heartbeat data, matches them against a curated knowledge base (runbooks, SOPs, known-error database) via RAG, explains the likely cause in plain language, and walks a non-technical operator through a self-fix. If that doesn't resolve it, the operator raises a ticket in one tap, auto-filled with context, diagnostic summary, chat transcript, and photos.

See [`scope-document.md`](scope-document.md) and [`detailed-plan-document.md`](detailed-plan-document.md) for the full product scope and build plan.

## Repository structure

```
backend/    FastAPI + SQLAlchemy (async) + PostgreSQL/pgvector + LangGraph API and worker
frontend/   React + Vite + TypeScript PWA (operator + staff flows)
documents/  Source scope/plan documents and prompts used to drive each service's build
```

Each service has its own README with full setup instructions: [`backend/README.md`](backend/README.md), [`frontend/README.md`](frontend/README.md).

## Stack

- **Backend**: FastAPI, SQLAlchemy (async), PostgreSQL + pgvector, Redis, MinIO, LangGraph, Alembic — containerized via Docker Compose.
- **Frontend**: React 19, Vite, TypeScript (strict), Tailwind CSS + shadcn/ui, TanStack Query/Table, Zustand, React Router v7, react-i18next (EN/HI), vite-plugin-pwa.

## Quickstart

Backend:

```bash
cd backend
cp .env.example .env   # fill in real secrets (OPENAI_API_KEY, etc.)
make up                 # docker compose up --build
```

API: http://localhost:8000 (docs at `/docs`)

Frontend:

```bash
cd frontend
pnpm install
cp .env.example .env    # set VITE_API_URL to the backend above
pnpm dev
```

App: http://localhost:5173
