import { useEffect, type ReactNode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from '@/components/ui/sonner'
import { queryClient } from '@/lib/queryClient'
import { useAuthStore } from '@/features/auth/store/authStore'
import { refreshAccessToken } from '@/lib/axios'
import { sessionToken } from '@/lib/sessionToken'
import '@/lib/i18n'

/** On load, tries to silently resume a session from the persisted refresh
 * token (see sessionToken.ts) so a page reload doesn't force a re-login. */
function AuthBootstrap() {
  useEffect(() => {
    async function bootstrap() {
      if (!sessionToken.get()) {
        useAuthStore.getState().setBootstrapped()
        return
      }
      const refreshed = await refreshAccessToken()
      if (refreshed) {
        useAuthStore.getState().setSession(refreshed.access_token, refreshed.user)
      } else {
        sessionToken.clear()
        useAuthStore.getState().setBootstrapped()
      }
    }
    void bootstrap()
  }, [])

  return null
}

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthBootstrap />
      {children}
      <Toaster />
    </QueryClientProvider>
  )
}
