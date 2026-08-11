# Interview Q&A — AI Field Assistant (Frontend)

Prep notes for talking through this project in an interview. Organized by topic, roughly easy → deep.

---

## 1. Project Overview

**Q: What does this app do?**
A: It's the frontend for an AI-assisted field troubleshooting & ticketing platform for manufacturing plants (JBM Group), covering machine vision/inspection lines and related shop-floor equipment. It serves two audiences: an admin/plant-viewer dashboard (desktop, fully built) for managing plants, users, machine health, tickets and QR codes; and an operator flow (mobile) where a technician scans a QR sticker on a faulty machine and raises a ticket without logging in.

**Q: What's the data/asset model?**
A: `Plant → Machine`. Each machine carries a health status (`online` / `degraded` / `offline`). There are three user roles: `admin`, `plant_viewer`, `operator`.

**Q: What are the three roles and what can each do?**
A:
- `admin` — full access: manage plants, create users, generate QR codes, view/close all tickets, see machine health across every plant.
- `plant_viewer` — read-only, scoped to a single plant (`AuthUser.plantId`). Sees only that plant's machines/tickets; no Plants/Users/QR nav items.
- `operator` — the QR-scan persona. The `/a/:token` landing is currently public (no auth), so this role isn't gated behind login yet — it's reserved for when operator accounts are introduced.

**Q: What's actually "done" vs "future work"?**
A: Admin dashboard is fully built. The operator flow has a basic version working: resolve QR token → machine card → hub with Ask/Health/Report options. Chat/AI-assist is a keyword-stub today, not a real LLM integration yet — that's future work.

---

## 2. Mock Mode / "No Backend" Decision

**Q: Why is there no real backend wired up, and how does the app work without one?**
A: This was a deliberate decision to build the admin UI without waiting on the backend team. `src/lib/mockDb.ts` is the entire "backend" — an in-memory store (plants, users, machines, tickets, qrTokens) seeded with demo data on first load, and mirrored to `localStorage` (`mock_db_v1`) so state survives a reload.

**Q: How do components read/write to this mock store reactively?**
A: Reads go through `useMockDb(selector)`, a hook built on `useSyncExternalStore` that re-renders any consumer when the store mutates — same mental model as a Redux/Zustand selector, but hand-rolled without a state library. Writes go through named `mockDb.*` methods (`addPlant`, `addPlantViewer`, `setTicketStatus`, `generateQr`, `deletePlant`, etc.) rather than raw setters, so mutation is centralized and cascading deletes are consistent.

**Q: How is auth mocked?**
A: `src/features/auth/api/mockAuth.ts` exposes `mockLogin(email, password)`, which validates against the mock user store with no network call. The session (`{ access_token, user }`) is persisted to `localStorage` (`mock_session`); `AuthBootstrap` (in `src/app/providers.tsx`) restores it on app load, and `authStore` (Zustand-style) keeps token + user in memory for the rest of the app.

**Q: Isn't storing auth tokens in localStorage a security smell?**
A: Yes — and it's called out explicitly in the project docs as an intentional exception: "mock mode intentionally violates the older 'no localStorage for auth' rule — it's a demo convenience, not the production scheme." The real-backend scaffolding (`axios.ts`, `sessionToken.ts`, `apiError.ts`) already exists and follows a stricter pattern; it's just unused right now.

**Q: How would you cut over to a real backend?**
A: Per feature: replace `mockDb.*` / `mockLogin` calls with thin `apiClient` functions inside that feature's `api/` folder, and swap `useMockDb` selectors for TanStack Query hooks. The page/component shapes are designed not to change much — the mock layer's method signatures mirror what real endpoints would look like. The `openapi.json` → `src/types/api.d.ts` generation pipeline (via `openapi-typescript`) is already wired and dormant, ready to generate real types once the backend is live.

**Q: What's `pnpm sync:api-types` for if there's no backend call yet?**
A: It's kept warm for that future cutover: `fetch:openapi` pulls the live spec from `VITE_API_URL/openapi.json`, `generate:api-types` runs `openapi-typescript` against it to produce `src/types/api.d.ts`. Nothing consumes those types yet, but the pipeline is proven out.

---

## 3. Routing & Guards

**Q: Walk through the routing structure.**
A: `/login` — email+password, redirects to `/app/dashboard` on success. `/a/:token` — public, wrapped in `OperatorShell`, no auth guard at all (QR-scan landing). `/app/*` — guarded by `RequireAuth` (redirect to `/login` if not signed in) → `RequireRole allow={['admin','plant_viewer']}` → `StaffShell`, with child routes `dashboard`, `plants`, `machines`, `tickets`, `qr`, `users`. Plus `/403` and a catch-all `*` NotFound.

**Q: Why does `RequireRole` assume `user` is non-null?**
A: Because it only ever renders beneath `RequireAuth` in the tree — by the time you reach it, auth has already guaranteed a signed-in user. It's a positional/structural guarantee rather than a runtime null-check, which keeps the component simpler (no defensive `user?.role` checks needed inside it).

**Q: Two shells — why?**
A: `StaffShell` is the sidebar dashboard chrome for all `/app/*` admin/plant-viewer pages — its nav items are role-filtered (each `NAV_ITEM` declares which roles can see it), and the header shows the signed-in user's name, role, and plant scope. `OperatorShell` is a narrow, chrome-free mobile shell (with an `OfflineBanner`) for the public QR-scan flow — completely different audience and device profile, so it doesn't share the sidebar/nav concerns at all.

---

## 4. Plant Scoping Pattern

**Q: How does a `plant_viewer` end up seeing only their plant's data?**
A: Every plant-scoped page computes `const scopePlant = user?.role === 'plant_viewer' ? user.plantId : null`, then filters its `useMockDb` selector by that value. Admins pass `null`, which the selector treats as "no filter, show everything." It's a convention repeated per-page rather than a shared HOC — simple, explicit, and easy to audit per file.

**Q: Why not centralize that filtering logic in a single hook?**
A: (Judgment call to discuss live.) The current codebase favors an explicit, repeated one-liner over an abstraction — consistent with the project's broader "don't introduce abstractions beyond what the page needs" philosophy. A fair critique: if a fourth or fifth scoped page appears, extracting a `useScopedPlantId()` hook would remove the duplication without adding real complexity.

---

## 5. Forms

**Q: What's the form stack?**
A: `react-hook-form` + `zod` via `@hookform/resolvers`' `zodResolver`. Validation errors come from `formState.errors`.

**Q: Is there a `<Form>` wrapper component like typical shadcn setups ship?**
A: No — this shadcn registry preset (`radix-nova`) doesn't include an RHF-bound `Form` component, so the project uses framework-agnostic primitives instead: `Field` / `FieldLabel` / `FieldError` / `FieldGroup` from `src/components/ui/field.tsx`, wired manually with `register()` and `formState.errors`. See `StaffLoginForm.tsx`, `PlantsPage.tsx`, `UsersPage.tsx` for the pattern.

**Q: How do you drive a shadcn `<Select>` from React Hook Form without a native `<select>` element?**
A: `<Select>` isn't a real form input RHF can `register()` directly, so the pattern is: read the current value with `form.watch(name)`, and push changes with `form.setValue(name, v, { shouldValidate: true })` on the `onValueChange` callback. Note: this triggers an ESLint `react-hooks/incompatible-library` warning on `form.watch` (because watch subscriptions don't fit the plain hook-dependency model) — that's a known, accepted warning here, not a bug.

**Q: How is user-facing feedback (success/error) shown?**
A: `sonner` toasts, imported as `import { toast } from 'sonner'`.

---

## 6. Shared UI / Design System

**Q: What handles list views like Users, Machines, Tickets?**
A: `src/components/DataTable.tsx`, a shared wrapper around TanStack Table (`@tanstack/react-table`) — handles the common table rendering so each feature just supplies columns/data.

**Q: How is machine health status displayed consistently?**
A: `src/components/StatusBadge.tsx` is the single source of truth for the green/amber/red online/degraded/offline convention, paired with matching `bg-status-*` Tailwind classes used on the fleet-health bars in the dashboard. Any new status UI is expected to reuse this rather than invent ad hoc colors.

**Q: What's the convention for "active" vs "inactive" pills (plants, users, QR tokens)?**
A: Active/enabled uses `<Badge variant="secondary" className="border-transparent bg-status-online/15 text-status-online">` (green-tinted), not the default blue badge variant. Inactive/none uses `variant="outline"`. This is a deliberate override of the default shadcn Badge styling to keep it consistent with the status-color language used elsewhere.

**Q: What's the delete-confirmation pattern?**
A: A ghost trash-icon button tinted `text-status-offline`, which opens a confirmation `Dialog` (never a native `confirm()` — better accessibility/styling control), whose confirm button is `variant="destructive"` and calls the relevant `mockDb.delete*` method. Cascading deletes are handled inside `mockDb` itself, e.g. `deletePlant` also removes that plant's machines, QR tokens, and tickets; `deleteMachine` removes its QR tokens. New delete actions are expected to mirror this cascade logic.

**Q: Where do design tokens (colors) live, and what Tailwind version is this?**
A: Tailwind v4 — no `tailwind.config.ts`; tokens are CSS variables under `@theme inline` in `src/index.css` (deep-blue `--primary`, neutral background, and the `--status-online/--status-degraded/--status-offline` trio). There's also a `.tap-target` utility enforcing a ≥44px touch target minimum, anticipating the mobile-first operator flow.

**Q: How do you add a new shadcn component?**
A: `pnpm dlx shadcn@latest add <name> -y`. Gotcha: if it ever writes into a literal `./@/` directory instead of `src/components/ui`, it means the root `tsconfig.json`'s path alias fell out of sync with `tsconfig.app.json`'s `@/*` alias — both need to declare the same alias.

---

## 7. The QR / Operator Flow

**Q: How does QR generation and scanning work?**
A: Admins generate a QR per machine on the `QrCodesPage` using `qrcode.react`, encoding the machine's `/a/<token>` URL (where token comes from `mockDb.generateQr`). "Download QR" renders a hidden 640×640 `QRCodeCanvas`, redraws it onto a fresh 640×640 canvas, and saves it via a `toDataURL`-based object download.

**Q: What's the gotcha with testing QR scanning on a phone?**
A: The QR encodes `location.origin + /a/<token>` — so a QR generated while viewing the app on `localhost` only resolves on that same machine, not from a phone on the network. Fix: run `pnpm dev --host` and open the app via its printed LAN IP before generating the QR, so the encoded origin is actually reachable from the scanning device.

**Q: Walk through what happens after a QR is scanned.**
A: `QrLandingPage` at `/a/:token` calls `mockDb.resolveToken(token)`. On an unknown/revoked token it shows a friendly error state. On success it shows the machine card, then a hub of three options controlled by local `view` state (`menu | ask | health | report`), each with its own Back button:
  - **Ask me** (`AskPanel`) — chat UI against `getMockReply`, a keyword-stub in `features/chat/api/mockAssistant.ts`. Meant to be swapped for a real streaming AI backend later.
  - **Machine Health** (`HealthPanel`) — the same status/health%/temperature/uptime/last-seen/line readings admins see, in a mobile card layout.
  - **Report an Issue** (`ReportPanel`) — raises a ticket via `mockDb.createTicket`; this ticket then shows up in the admin `TicketsPage`. Called out as "the fully-working reference flow" — i.e. the most complete end-to-end mock feature to point to.

**Q: Are the `chat` and `kb` feature folders used anywhere?**
A: No — they contain earlier stub pages/mocks that predate the current operator flow and are intentionally left unrouted, to be repurposed later rather than deleted.

---

## 8. i18n / PWA / Non-functional Concerns

**Q: What's the i18n setup, and is it fully applied?**
A: `react-i18next`, resources at `src/locales/{en,hi}.json`, loaded eagerly in `src/lib/i18n.ts`. Honest caveat: the newer admin pages currently use hard-coded English strings rather than `t()` calls — this is flagged as a known gap to close before calling it production-ready, not an oversight to hide.

**Q: What PWA behavior exists?**
A: `vite-plugin-pwa` (configured in `vite.config.ts`) caches static assets only; API calls are explicitly excluded from the cache (relevant later once real API calls exist, so stale data isn't served offline). Icons in `public/icons/` are placeholders pending real brand assets.

---

## 9. Tooling & Testing

**Q: What's the full command surface?**
A:
- `pnpm dev` — Vite dev server (`:5173`, `--port` to change; `--host` for LAN access, needed for QR scanning from a phone).
- `pnpm build` — `tsc -b && vite build` (typechecks before bundling).
- `pnpm lint` / `lint:fix` — ESLint flat config with `typescript-eslint`, `jsx-a11y`, `react-hooks` plugins.
- `pnpm format` / `format:check` — Prettier.
- `pnpm typecheck` — `tsc -b --noEmit` in strict mode.
- `pnpm test` — Vitest.
- `pnpm e2e` — Playwright (needs `pnpm exec playwright install chromium` once).
- `pnpm fetch:openapi` / `generate:api-types` / `sync:api-types` — dormant OpenAPI → TS types pipeline for the eventual real backend.

**Q: Why `tsc -b` and not just `tsc`?**
A: `-b` is build-mode / project-references mode — it respects `tsconfig` project references (there's a root `tsconfig.json` plus `tsconfig.app.json`), enabling incremental builds and correct cross-project type resolution rather than treating the repo as one flat compile.

---

## 10. Likely Follow-up / "Gotcha" Questions

**Q: What would break first if two admins edited data at the same time?**
A: Nothing meaningful — the mock store is per-browser in-memory + localStorage, not shared across clients/tabs in real time. There's no optimistic-concurrency or conflict resolution because there's no real multi-user backend yet; that's exactly the kind of problem the real API layer will need to solve (likely via TanStack Query's cache invalidation plus real server-side transactions).

**Q: Why `useSyncExternalStore` instead of pulling in Zustand or Redux for the mock DB?**
A: It's the minimal built-in React primitive for subscribing a component to an external mutable store with correct concurrent-rendering semantics — no extra dependency needed for what's ultimately a temporary mock layer slated for replacement by TanStack Query.

**Q: If you had to name the biggest technical risk in the current codebase, what would it be?**
A: The AI-assist chat ("Ask me") is a hardcoded keyword-matching stub, not a real model — that's the single biggest gap between the current demo and the actual product value proposition (AI-assisted troubleshooting). The rest of the app (auth, tickets, QR, plant/machine CRUD) is comparatively mechanical CRUD work that's already done well.

**Q: How would you prioritize the path to production?**
A: Roughly: (1) reconnect the real FastAPI backend feature-by-feature via the already-scaffolded `apiClient`/TanStack Query seam, starting with auth since everything else depends on it; (2) replace the chat stub with a real streaming LLM integration; (3) sweep hard-coded strings into i18n; (4) replace placeholder PWA icons with brand assets; (5) add operator-account gating once that role needs to log in for anything beyond the anonymous QR flow.
