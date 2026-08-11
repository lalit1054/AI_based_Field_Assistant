# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Frontend for an AI-assisted field troubleshooting & ticketing platform for **manufacturing plants** (JBM Group) — machine vision / inspection lines and related shop-floor equipment (e.g. "VI 10 Parts Inspection"). Two audiences:

- **Admin / staff** on desktop — the dashboard for managing plants, users, machine health, tickets, and QR codes. **Fully built and wired to the real backend.**
- **Operator** on a mid-range Android phone who scans a QR sticker on a faulty machine to report an issue, ask a troubleshooting question, or check machine health. **Fully built**: the public `/a/:token` landing resolves the QR token to its machine; a lightweight phone-number sign-in (`/auth/login-phone`, no OTP/password, self-registers on first use) gates the Ask/Health/Report actions.

Asset model: **Company → Plant → Line → Machine**. Machine `status` is an asset **lifecycle** state (`active | maintenance | decommissioned`), separate from live **health** telemetry (`is_online`, cpu/memory/disk %, last heartbeat) reported by `POST /health/heartbeat` and read via `GET /health/machines`.

## Roles

7 backend roles (`UserRole` in `src/features/auth/store/authStore.ts`, mirrors `app/db/enums.py`): `operator`, `field_tech`, `support_l2`, `support_l3`, `plant_manager`, `admin`, `company_viewer`. The UI collapses these into three tiers (`src/features/auth/roles.ts`):

- `admin` — full nav (Plants / Users / QR / Machines writes), sees every plant.
- `plant_manager`, `support_l2`, `support_l3`, `field_tech`, `company_viewer` (`SCOPED_STAFF_ROLES`) — the "scoped staff" shell: same dashboard/machines/tickets pages as admin, but read-mostly and limited to plants they've been granted access to (`user_plant_access`, see `useScopedPlants`). Ticket write actions (close/reassign) are further gated to `canWrite()` (`admin`, `support_l2`, `support_l3`, `plant_manager`), matching the backend's `WRITE_ROLES`.
- `operator` — the QR-scan flow, phone-authenticated, not part of the staff shell.

## Commands

```bash
pnpm install
cp .env.example .env            # VITE_API_URL=http://localhost:8000 — the backend must be running (see ../backend)

pnpm dev                        # dev server on :5173 (pass --port to change); vite.config.ts proxies /api -> VITE_API_URL
pnpm build                      # tsc -b && vite build
pnpm preview

pnpm lint / pnpm lint:fix       # ESLint (flat config, typescript-eslint, jsx-a11y, react-hooks)
pnpm format / pnpm format:check # Prettier
pnpm typecheck                  # tsc -b --noEmit (strict mode)

pnpm test                       # Vitest
pnpm e2e                        # Playwright — requires `pnpm exec playwright install chromium` once

# API-types pipeline — run this after any backend schema/route change:
pnpm fetch:openapi              # pulls live spec from VITE_API_URL/openapi.json -> ./openapi.json
pnpm generate:api-types         # openapi-typescript ./openapi.json -> src/types/api.d.ts
pnpm sync:api-types             # both of the above
```

## API integration

**No mock layer** — `src/lib/mockDb.ts` / `mockAuth.ts` / `mockAssistant.ts` / `mockArticles.ts` were deleted once every feature was wired to the real FastAPI backend at `../backend`.

**Convention per feature**: a thin `src/features/<name>/api/*.ts` module exports plain async functions built on `apiClient` (`src/lib/axios.ts`) and typed off the openapi-typescript output (`import type { components } from '@/types/api'`), e.g. `export type Plant = components['schemas']['PlantOut']`. Pages call these through TanStack Query — `useQuery({ queryKey: [...], queryFn: ... })` for reads, `useMutation` + `queryClient.invalidateQueries` for writes. There's no query-key-factory or generic `useApiQuery` wrapper; keys are plain arrays like `['admin', 'plants']`, `['tickets']`, `['health', 'machines', machineId]`.

**Auth**: real JWT access token (kept in-memory only, in `authStore`) + rotating opaque refresh token (persisted to `sessionStorage` via `src/lib/sessionToken.ts` — deliberately not `localStorage`, and the access token is never persisted at all). `src/lib/axios.ts`'s `apiClient` injects `Authorization: Bearer <accessToken>` on every request and silently refreshes-and-retries once on a 401 (`refreshAccessToken`, exported for reuse). `AuthBootstrap` in `src/app/providers.tsx` calls `refreshAccessToken()` on load if a refresh token exists, so a reload doesn't force a re-login. Staff sign-in is `POST /auth/login` (`useStaffLogin` in `features/auth/hooks/useAuthMutations.ts`); operator sign-in is `POST /auth/login-phone` (`usePhoneLogin`) — both return `{access_token, refresh_token, user}` and go through the same `applySession` helper. `getApiErrorMessage` (`src/lib/apiError.ts`) unwraps the backend's `{error, detail}` envelope for toasts/form errors.

**Regenerating types**: whenever a backend route or schema changes, run `pnpm sync:api-types` (backend must be running) before touching the affected frontend feature, so `src/types/api.d.ts` — and therefore every `components['schemas'][...]` type used in `api/*.ts` files — stays accurate.

## Architecture

**Two shells, one router.** `src/components/layout/StaffShell.tsx` is the sidebar dashboard shell for all staff pages under `/app/*`; its nav is **role-filtered** (each `NAV_ITEM` declares which roles see it, via `SCOPED_STAFF_ROLES` from `features/auth/roles.ts`) and the header shows the signed-in user's name + role + their granted plants (fetched via `GET /admin/users/{id}/plant-access`). `src/components/layout/OperatorShell.tsx` is the narrow, chrome-free mobile shell (with `OfflineBanner`) used for the public `/a/:token` operator landing.

**Routes** (`src/app/router.tsx`): `/login` (email+password) → on success redirect to `/app/dashboard`. **`/a/:token` is public** (wrapped in `OperatorShell`, outside any guard) — the QR-scan landing; the phone-login gate lives _inside_ `QrLandingPage`, not the router. `/app/*` is guarded by `RequireAuth` (redirects to `/login`) → `RequireRole allow={STAFF_ROLES}` → `StaffShell`, with children `dashboard`, `plants`, `machines`, `tickets`, `qr`, `users`. `/403` and a `*` NotFound round it out.

**Feature folder convention** (`src/features/<name>/`): `pages/` (routed components), `api/` (backend calls), plus `components/` / `hooks/` as needed. Current features:

- `auth` — `LoginPage`, `StaffLoginForm`, `authStore`, `roles.ts` (role-tier helpers), real `api/auth.ts` (`staffLogin`, `phoneLogin`, `logout`), `hooks/useAuthMutations.ts`, `hooks/useScopedPlants.ts` (plants visible to the current user — all of them for `admin`, else their `user_plant_access` grants).
- `dashboard` — `DashboardPage` (stat cards + online/offline fleet-health bars + recent tickets), backed by a single `GET /dashboard/stats` call (`api/dashboard.ts`) — no client-side aggregation.
- `admin` — `PlantsPage` (card list; add + **deactivate** — there's no delete endpoint, `PATCH .../plants/{id} {is_active:false}`), `UsersPage` (table; create staff user + grant plant access, enable/disable), plus `api/{companies,plants,lines,users}.ts`. Plant creation auto-uses the first (only) `Company` from `GET /admin/companies` — there's no company-management UI yet.
- `assets` — `MachinesPage` (asset table with plant filter; admin can **add** a machine under a plant + optional line; shows lifecycle `status` badge plus a live-health column joined client-side from `GET /health/machines`; "delete" is `PATCH status: maintenance/active` since there's no delete endpoint), `api/machines.ts`, `api/health.ts`.
- `tickets` — `TicketsPage` (All/Open/Closed tabs over the real 7-value `TicketStatus`; write-capable roles can close), `api/tickets.ts`.
- `qr` — `QrCodesPage` (admin generates a real, scannable QR per machine via `qrcode.react`, using `POST/GET /qr/machines/{id}/tokens`; the backend's `QrTokenOut` has no `url` field so the frontend still builds `${origin}/a/<token>` itself — see `qrTokenUrl()` in `api/qr.ts`. **Download QR** exports a 640×640 PNG the same way as before).
- `qr-landing` — `QrLandingPage` (public operator flow at `/a/:token`): resolves the token via `GET /a/{token}` (`api/qrLanding.ts`); if the operator has no session yet, shows `PhoneGate` (calls `usePhoneLogin`) before anything else — Ask/Health/Report all require auth server-side. Then a **hub of three options** (`menu | ask | health | report` local view state), each with a Back button:
  - **Ask me** (`AskPanel`) — creates a real `POST /chat/sessions` on mount, sends messages via `POST /chat/sessions/{id}/messages` (`features/chat/api/chat.ts`). The backend reply is a **canned keyword match** (`app/services/canned_reply.py`), not a real AI agent yet (Milestone 7 was deliberately bounded — see `backend/CLAUDE.md`).
  - **Machine Health** (`HealthPanel`) — reads `GET /health/machines/{id}`; shows "no health data" until an agent sends a heartbeat.
  - **Report an Issue** (`ReportPanel`) — `POST /tickets`, shown on the admin `TicketsPage`.
- `kb` — `KbPage` (list view over `GET /kb/documents`, `api/documents.ts`) — **not routed** in `router.tsx`; ready to route when the product wants a staff-facing KB browser.
- `chat` — only `api/chat.ts` remains (used by `qr-landing`'s `AskPanel`); the standalone unrouted `ChatPage` stub was removed as dead code once the real Ask flow shipped.

**Note on scannability:** the QR encodes `location.origin + /a/<token>`, so QRs generated while viewing on `localhost` are only reachable from the same machine. To scan from a phone, run `pnpm dev --host` and open the app via the printed LAN URL before generating, so the encoded origin is the reachable IP.

**Plant scoping pattern:** any page a scoped-staff role can see should use `useScopedPlants()` (`features/auth/hooks/useScopedPlants.ts`) to get `{ plants, isAdmin }`, then filter machine/ticket lists by `plants.map(p => p.id)` client-side (the backend also enforces this server-side for `/tickets` and `/dashboard/stats`, but not yet for `/assets/machines`). Follow this in any new plant-scoped view rather than re-deriving scope from `user.role` directly.

**Forms**: `react-hook-form` + `zod` (`zodResolver`). There is **no** RHF-bound `Form` component in this shadcn registry — use the framework-agnostic `Field`/`FieldLabel`/`FieldError`/`FieldGroup` primitives from `src/components/ui/field.tsx` with `register`/`formState.errors` (see `StaffLoginForm.tsx`, `PlantsPage.tsx`, `UsersPage.tsx`). For a shadcn `<Select>` inside RHF, drive it with `form.watch(name)` + `form.setValue(name, v, { shouldValidate: true })` (the ESLint `react-hooks/incompatible-library` warning on `form.watch` here is known and accepted). User feedback uses `sonner` toasts (`import { toast } from 'sonner'`); API failures go through `getApiErrorMessage(error, fallback)`.

**Shared components**: `src/components/DataTable.tsx` wraps TanStack Table for list views (Users, Machines, Tickets). `src/components/StatusBadge.tsx` is the online/degraded/offline convention — now only used for **live health** (online/offline) and the QR-landing chat bubbles' status, not asset lifecycle (which uses a plain `Badge` — see `LIFECYCLE_BADGE` in `MachinesPage.tsx`).

**UI conventions:**

- **"Active" pills are green**: an active/enabled entity (plant, user, QR token) uses `<Badge variant="secondary" className="border-transparent bg-status-online/15 text-status-online">` — not the default (blue) badge. Inactive/none uses `variant="outline"`.
- **No hard deletes**: the backend exposes no DELETE endpoints for plants/machines/tickets — admin "removal" actions are `PATCH` to a deactivated/maintenance state instead, still behind a confirmation `Dialog` (never a native `confirm()`) with a `variant="destructive"` confirm button.

**shadcn/ui** is the newer `radix-nova` preset. Add components with `pnpm dlx shadcn@latest add <name> -y` — if it ever writes into a literal `./@/` directory, the root `tsconfig.json`'s `compilerOptions.paths` fell out of sync with `tsconfig.app.json`'s `@/*` alias; both must declare it.

**Design tokens** live in `src/index.css` as CSS variables under `@theme inline` (Tailwind v4, no `tailwind.config.ts`): deep-blue `--primary`, neutral background, and the `--status-online`/`--status-degraded`/`--status-offline` trio. A `.tap-target` utility enforces the ≥44px touch target minimum (used throughout the operator flow).

**i18n**: `react-i18next`, resources at `src/locales/{en,hi}.json` loaded eagerly in `src/lib/i18n.ts`. Note the admin pages currently use **hard-coded English strings** rather than `t()` — run them through i18n before this is considered production-ready.

**PWA**: `vite-plugin-pwa` (`vite.config.ts`) caches static assets only; API calls are excluded. Placeholder icons in `public/icons/` should be replaced with real JBM brand assets before shipping.
