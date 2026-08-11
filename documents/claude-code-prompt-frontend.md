# Claude Code Prompt — Frontend

> How to use: create an empty folder (e.g. `troubleshoot-frontend/`), open Claude Code in it, and paste the master prompt. Have the backend running (or at least its OpenAPI JSON exported) — the frontend consumes that contract. Build screen-by-screen using the milestone prompts at the end.

---

## MASTER PROMPT (paste into Claude Code)

You are building the frontend for an **AI-assisted field troubleshooting & ticketing platform** for Intelligent Traffic Systems (ANPR, AVC, SVDS, MLFF). The primary user is a **non-technical toll-plaza operator on a mid-range Android phone over 4G** who scanned a QR sticker on a faulty device. Secondary users are support engineers and admins on desktop. This must be an industry-grade, mobile-first **PWA**.

### Tech stack (do not substitute)
- **React 19 + Vite + TypeScript (strict)**
- **Tailwind CSS + shadcn/ui** (initialise properly, use the CLI to add components)
- **@assistant-ui/react** for the chatbot UI, connected to the backend's SSE chat endpoint via a **custom runtime/adapter** (the backend streams events: `token`, `tool_start`, `tool_end`, `suggested_actions`, `done`)
- **TanStack Query v5** (server state), **Zustand** (auth/session UI state)
- **React Router v7**, **React Hook Form + Zod**
- **react-i18next** — English + Hindi from day one; every user-facing string via translation keys
- **vite-plugin-pwa** (installable, offline app shell, cache-first static assets)
- **browser-image-compression** for photos before upload
- **Recharts** for dashboard charts; **TanStack Table** for queues/registries
- **Axios** instance with JWT interceptor + auto refresh-token retry
- Generate the API types from the backend OpenAPI spec using `openapi-typescript`; never hand-write response types
- Vitest + React Testing Library; Playwright for 3 core E2E flows

### Design language
- Clean industrial-professional look: neutral background, one strong primary color (deep blue), high-contrast text, large touch targets (min 44px), big readable fonts — this is used outdoors in sunlight.
- Status colors used consistently everywhere: green=online/resolved, amber=degraded/in-progress, red=offline/critical.
- Skeleton loaders everywhere; optimistic UI on ticket comments; graceful offline banners ("You're offline — your report will be sent when connection returns" for the ticket form draft, persisted in memory + IndexedDB via idb-keyval).
- Every screen must be genuinely usable one-handed on a 360px-wide phone. Desktop layouts for staff screens use a sidebar shell.

### API contract (backend base URL via `VITE_API_URL`)
Auth: `POST /auth/otp/request`, `POST /auth/otp/verify`, `POST /auth/login`, `POST /auth/refresh`
QR: `GET /a/{token}` → `{asset: {id, app_type, name}, site: {name, code}, lane: {number}|null, health: {is_online, last_heartbeat, services}}`
Chat: `POST /chat/sessions`, `POST /chat/sessions/{id}/messages` (SSE response), `/rate`, `/close`, `/attachments`
Uploads: `POST /uploads/presign` → PUT file to presigned URL → register attachment
Tickets: standard CRUD + `/comments`, status transitions; `GET /tickets?mine=true`
Health/dashboard/admin endpoints per OpenAPI spec.

### Screens & routes

**Operator flow (mobile-first, the core product):**
1. `/a/:token` — QR landing. Shows big context card: app type icon, site name, lane number, live health badge ("Device last seen 2 min ago" / "Device OFFLINE"). One primary button: "Report a problem / समस्या बताएं". If not logged in → inline OTP login (phone → 6-digit code, auto-read layout, resend timer) then return here. Language toggle EN/हिंदी prominent.
2. `/a/:token/manual` fallback + `/report` — manual selection: App Type → Site → Lane (lane step skipped when the app type is site-level), searchable dropdowns.
3. `/chat/:sessionId` — the troubleshooting chat (assistant-ui): streaming responses, markdown, **suggested-action chips** rendered from the `suggested_actions` SSE event (tapping a chip sends it as the user message), camera/photo attach button (compress to ≤300KB, show thumbnail in the thread), typing/tool-running indicator ("Checking device logs…" when `tool_start` event names get_logs), sticky "Raise a ticket instead" secondary action. On agent's `create_ticket` completion, render a success card with ticket number, SLA time, and "Track ticket" button. End-of-session 1–5 star rating.
4. `/tickets/mine` + `/tickets/:id` (operator view) — status timeline, comments (non-internal), photos, add comment/photo.

**Staff flows (desktop-friendly, `/app` shell with sidebar):**
5. `/app/tickets` — queue: filters (status, priority, site, app type, assignee), TanStack Table, bulk assign; `/app/tickets/:id` — full detail: diagnosis summary, linked chat transcript viewer, log-bundle download, internal comments, status transition buttons with validation, SLA countdown badges.
6. `/app/dashboard` — cards (open tickets, offline assets, self-fix rate, avg resolution), site health heatmap (grid of sites colored by open critical incidents), 30-day trend line, top recurring issues per app type.
7. `/app/assets` — registry table + asset detail (health history, QR management: view/regenerate token, "Add to sticker sheet" bulk action → downloads PDF from backend).
8. `/app/kb` — KB document list, upload (PDF/DOCX with progress), known-errors CRUD with markdown editor for fix steps.
9. `/app/admin` — clients/sites/lanes/users CRUD, user-site access assignment. Guard all `/app` routes by role.

### Auth & roles
- Zustand auth store (access token in memory, refresh token in httpOnly cookie set by backend if available, else localStorage is NOT allowed — use in-memory + silent refresh on load).
- Route guards by role: operator/field_tech → operator flow + own tickets; support_l2/l3 → tickets/dashboard/kb; admin → everything; client_viewer → read-only dashboard+tickets.

### Non-negotiables
- TypeScript strict, no `any`. ESLint + Prettier configured.
- All strings through i18next (provide complete `en.json` and `hi.json`).
- Lighthouse mobile score ≥ 90 for the operator flow; code-split staff routes so the operator bundle stays small.
- Error boundaries + toast system (sonner); every mutation has loading/disabled states.
- `pnpm dev` proxies `/api` to `VITE_API_URL`; `.env.example`; README with setup.
- Component structure: `src/features/<feature>/` (components, hooks, api) + `src/components/ui` (shadcn) + `src/lib`.
- Vitest tests for auth store, SSE parsing hook, and chip-interaction logic; Playwright E2E for: OTP login → QR landing → chat with mocked SSE → raise ticket; staff ticket status transition; admin asset+QR creation.

### Build order (confirm each milestone renders and passes lint before moving on)
1. Scaffold: Vite + TS + Tailwind + shadcn + router + i18n + PWA + axios/query setup + auth store + login screens (OTP + staff)
2. OpenAPI type generation wiring + API layer per feature
3. QR landing + manual selection flow + health card
4. Chat screen with assistant-ui custom SSE runtime + attachments + chips + ticket success card
5. Operator ticket views
6. Staff shell + ticket queue/detail
7. Dashboard
8. Assets + QR management, KB, admin
9. Offline handling, error boundaries, polish pass (empty states, skeletons)
10. Tests + Lighthouse pass + README

Start with milestone 1. Show me the folder tree and the shadcn components you plan to add before generating code.

---

## Follow-up prompts to use per milestone
- "Milestone 4: before coding, explain how you will implement the assistant-ui custom runtime over our SSE event protocol (token / tool_start / tool_end / suggested_actions / done), including reconnection and error handling. Then implement it with a mock SSE server for dev."
- "Run the Playwright E2E suite against the seeded backend (docker-compose from the backend repo) and fix any failures."
- "Do a mobile polish pass: test every operator screen at 360px width, fix touch targets under 44px, and verify Hindi strings don't overflow."
