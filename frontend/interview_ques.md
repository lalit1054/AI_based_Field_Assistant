# Interview Questions & Answers — AI Field Assistant Frontend

### 1. What does this application do?
It's the frontend for an AI-assisted field troubleshooting & ticketing platform for manufacturing plants (JBM Group). It serves two audiences: an admin/plant-viewer dashboard for managing plants, users, machine health, tickets, and QR codes, and a mobile operator flow where a shop-floor worker scans a QR sticker on a machine to report an issue.

### 2. What is the asset model in this system?
Plant → Machine. Each machine carries a health status of online, degraded, or offline. Users have one of three roles.

### 3. What are the three user roles and what can each do?
Defined as `UserRole` in `src/features/auth/store/authStore.ts`:
- **admin** — full access: manage plants, create users, generate QR codes, view/close all tickets, see machine health across every plant.
- **plant_viewer** — read-only, scoped to a single plant (via `AuthUser.plantId`); sees only that plant's machine health and tickets, no Plants/Users/QR nav.
- **operator** — the QR-scan flow, currently public/ungated, reserved for when operator accounts are introduced.

### 4. Is this app currently connected to a real backend?
No. It runs entirely in "mock mode" — client-side against an in-memory mock data layer with no live API wiring. This was a deliberate choice to build the admin UI without waiting on the backend. A sibling FastAPI backend exists at `../backend`, and the OpenAPI type-generation pipeline is kept dormant for later reconnection.

### 5. How does mock mode work under the hood?
`src/lib/mockDb.ts` acts as the whole "backend" — an in-memory store (plants, users, machines, tickets, qrTokens) seeded with demo data and mirrored to `localStorage` under the key `mock_db_v1`, so state survives a reload. Reads are reactive through `useMockDb(selector)`, a `useSyncExternalStore` hook that re-renders on any mutation; writes go through methods like `addPlant`, `setTicketStatus`, `generateQr`, etc.

### 6. How does mock authentication work?
`src/features/auth/api/mockAuth.ts` exposes `mockLogin(email, password)`, which validates against the mock user store with no network call. The session (`{ access_token, user }`) is persisted to `localStorage` under `mock_session` and restored on load by `AuthBootstrap` in `src/app/providers.tsx`. The demo admin credentials are `lalit.kumar4@jbmgroup.com` / `jbm@123`.

### 7. How would you migrate from mock mode to a real backend?
For each feature, replace `mockDb.*` / `mockLogin` calls with thin `apiClient` functions inside that feature's `api/` folder, and swap `useMockDb` for TanStack Query hooks. Page/component shapes are designed to need little to no change during this swap.

### 8. What are the two UI "shells" and when is each used?
- `StaffShell` (`src/components/layout/StaffShell.tsx`) — the sidebar dashboard shell for all admin/plant-viewer pages under `/app/*`; nav items are role-filtered and the header shows the signed-in user's name, role, and plant scope.
- `OperatorShell` (`src/components/layout/OperatorShell.tsx`) — a narrow, chrome-free mobile shell with an `OfflineBanner`, used for the public `/a/:token` operator landing page.

### 9. How is routing structured?
`/login` handles email+password auth and redirects to `/app/dashboard` on success. `/a/:token` is public (wrapped in `OperatorShell`, no auth guard) for the QR-scan landing. Everything under `/app/*` is guarded by `RequireAuth` (redirect to `/login` if unauthenticated) then `RequireRole allow={['admin','plant_viewer']}`, wrapping `StaffShell` with child routes: dashboard, plants, machines, tickets, qr, users. `/403` and a catch-all NotFound route round it out.

### 10. What does `RequireRole` assume about where it's used?
It assumes it always runs beneath `RequireAuth`, so it can safely treat `user` as non-null when checking role access.

### 11. Describe the QR code operator flow end to end.
An admin generates a scannable QR (via `qrcode.react`) on the QR Codes page that encodes the machine's `/a/<token>` URL. An operator scans it, landing on the public `QrLandingPage`, which resolves the token via `mockDb.resolveToken` (showing a friendly error for unknown/revoked tokens) and displays the machine card with a hub of three options: Ask Me (chat stub), Machine Health (read-only status card), and Report an Issue (creates a real ticket via `mockDb.createTicket` that shows up in the admin Tickets page).

### 12. Why does the QR code need to be generated from the correct origin?
The QR encodes `location.origin + /a/<token>`. If generated while viewing on `localhost`, it's only reachable from that same machine. To make it scannable from a phone, run `pnpm dev --host` and open the app via the printed LAN URL before generating so the encoded origin is actually reachable.

### 13. What is the "plant scoping" pattern and where should it be applied?
Any page a `plant_viewer` can access computes `const scopePlant = user?.role === 'plant_viewer' ? user.plantId : null` and filters its `useMockDb` selector by that plant ID; admins pass `null` to see all plants. This pattern should be followed in any new plant-scoped view.

### 14. What form-handling conventions does the project follow?
`react-hook-form` combined with `zod` via `zodResolver`. There is no RHF-bound `Form` wrapper component in this shadcn registry, so forms use the framework-agnostic `Field`/`FieldLabel`/`FieldError`/`FieldGroup` primitives from `src/components/ui/field.tsx` with `register`/`formState.errors`. For a shadcn `<Select>` inside RHF, it's driven via `form.watch(name)` plus `form.setValue(name, v, { shouldValidate: true })`. User feedback uses `sonner` toasts.

### 15. What is the destructive-delete UI pattern used throughout the app?
A delete action is a ghost trash-icon button tinted `text-status-offline`. Clicking it opens a confirmation `Dialog` (never a native `confirm()`), whose confirm button uses `variant="destructive"` and calls the corresponding `mockDb.delete*` method. Deletes that would orphan data cascade inside `mockDb` — e.g. `deletePlant` also removes that plant's machines, QR tokens, and tickets; `deleteMachine` removes its QR tokens.

### 16. How does the app represent machine/entity status visually?
`src/components/StatusBadge.tsx` is the single source of truth for the green/amber/red online/degraded/offline convention, paired with matching `bg-status-*` classes for health bars — this should be reused rather than inventing ad hoc status colors. Separately, "active" pills (e.g. an enabled plant, user, or QR token) use a green secondary badge (`bg-status-online/15` with `text-status-online`), while inactive/none uses an outline badge.

### 17. What shared components exist for list views?
`src/components/DataTable.tsx` wraps TanStack Table and is reused across the Users, Machines, and Tickets pages for consistent table behavior (sorting, filtering, etc.).

### 18. What is the state of internationalization (i18n) in this codebase?
The project uses `react-i18next` with resource files at `src/locales/{en,hi}.json`, loaded eagerly in `src/lib/i18n.ts`. However, the newer admin pages currently use hard-coded English strings instead of the `t()` translation function — this needs to be addressed before the app is considered production-ready.

### 19. How are design tokens and styling configured?
Tailwind v4 is used without a `tailwind.config.ts`; design tokens live as CSS variables in `src/index.css` under `@theme inline`, including a deep-blue `--primary`, a neutral background, and the `--status-online` / `--status-degraded` / `--status-offline` trio. A `.tap-target` utility class enforces a minimum 44px touch target, anticipating the future one-handed mobile operator flow.

### 20. What are `chat` and `kb` features, and are they active?
They are earlier-stage stub features containing pages and mocks (e.g. `getMockReply` in `features/chat/api/mockAssistant.ts` powers the current Ask Me panel), but they are not wired into the router as standalone routes. They're left in place to be repurposed or expanded later as AI-assist and knowledge-base features mature.
