import { Suspense } from 'react'
import { RouterProvider } from 'react-router'
import { router } from '@/app/router'
import { AppProviders } from '@/app/providers'
import { ErrorBoundary } from '@/components/feedback/ErrorBoundary'
import { SkeletonBlock } from '@/components/feedback/SkeletonBlock'

function RouteFallback() {
  return (
    <div className="flex min-h-svh items-center justify-center p-6">
      <SkeletonBlock className="w-full max-w-sm" />
    </div>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <AppProviders>
        <Suspense fallback={<RouteFallback />}>
          <RouterProvider router={router} />
        </Suspense>
      </AppProviders>
    </ErrorBoundary>
  )
}

export default App
