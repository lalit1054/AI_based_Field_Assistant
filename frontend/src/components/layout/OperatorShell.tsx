import { Outlet } from 'react-router'
import { OfflineBanner } from '@/components/feedback/OfflineBanner'

/** One-handed, mobile-first shell for the operator flow. No sidebar, no chrome beyond a safe-area container. */
export function OperatorShell() {
  return (
    <div className="flex min-h-svh flex-col">
      <OfflineBanner />
      <main className="mx-auto flex w-full max-w-md flex-1 flex-col px-4 py-4">
        <Outlet />
      </main>
    </div>
  )
}
