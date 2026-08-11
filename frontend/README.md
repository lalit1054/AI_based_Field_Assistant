# AI Field Assistant — Frontend

Mobile-first PWA for field troubleshooting and ticketing of manufacturing plant machine vision / inspection lines and related shop-floor equipment. The operator flow targets a non-technical plant-floor operator on a mid-range Android phone over 4G; staff flows (tickets, dashboard, assets, KB, admin) are desktop-friendly.

## Stack

React 19 + Vite + TypeScript (strict) · Tailwind CSS + shadcn/ui · @assistant-ui/react (chat) · TanStack Query v5 + TanStack Table · Zustand · React Router v7 · React Hook Form + Zod · react-i18next (EN/HI) · vite-plugin-pwa · Recharts · Axios.

## Getting started

```bash
pnpm install
cp .env.example .env       # set VITE_API_URL to your backend
pnpm dev                   # http://localhost:5173, proxies /api -> VITE_API_URL
```

## Scripts

| Script                         | Purpose                                        |
| ------------------------------ | ----------------------------------------------- |
| `pnpm dev`                     | Start the Vite dev server                       |
| `pnpm build`                   | Type-check (`tsc -b`) and build for production  |
| `pnpm preview`                 | Preview the production build locally            |
| `pnpm lint` / `lint:fix`       | ESLint                                          |
| `pnpm format` / `format:check` | Prettier                                        |
| `pnpm typecheck`               | `tsc -b --noEmit`                               |
| `pnpm test`                    | Vitest (unit/component tests)                   |
| `pnpm e2e`                     | Playwright end-to-end tests                     |

## Project structure

```
src/
  app/            router, providers, route guards (RequireAuth, RequireRole)
  features/       one folder per domain (auth, qr-landing, chat, tickets, dashboard, assets, kb, admin)
    <feature>/api        API calls for the feature
    <feature>/components feature-local components
    <feature>/hooks      TanStack Query hooks, feature hooks
    <feature>/pages      routed page components
  components/
    ui/           shadcn/ui components (generated via the CLI, do not hand-edit lightly)
    layout/       OperatorShell (mobile), StaffShell (sidebar), LanguageToggle
    feedback/     ErrorBoundary, OfflineBanner, SkeletonBlock, ComingSoonPage
  lib/            axios instance (JWT + refresh retry), TanStack QueryClient, i18n, idb-keyval wrapper, cn
  locales/        en.json, hi.json — every user-facing string goes through i18next
  types/          generated API types (openapi-typescript) — never hand-written
```

## Auth model

- Access token lives in memory only (Zustand `authStore`).
- Refresh token is an httpOnly cookie set by the backend; the frontend never reads or stores it. `localStorage` is intentionally not used for tokens.
- On load, `AppProviders` silently calls `POST /auth/refresh` (cookie-authenticated) to restore the session before the route guards evaluate.
- `RequireAuth` redirects to `/login` (operator OTP) or `/staff/login` depending on which guarded subtree is hit; `RequireRole` gates by role on top of that.

## API types

Response/request types are generated from the backend's OpenAPI spec with `openapi-typescript` (wired in milestone 2) — never hand-write types in `src/types`.

## Design language

Neutral background, deep-blue primary, ≥44px touch targets, large readable type for outdoor/sunlight use. Status colors are consistent everywhere: green = online/resolved, amber = degraded/in-progress, red = offline/critical (see `StatusBadge`).
