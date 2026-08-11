import { useAuthStore } from '@/features/auth/store/authStore'
import { useLogout } from '@/features/auth/hooks/useAuthMutations'

export function useAuth() {
  const accessToken = useAuthStore((s) => s.accessToken)
  const user = useAuthStore((s) => s.user)
  const isBootstrapping = useAuthStore((s) => s.isBootstrapping)
  const logoutMutation = useLogout()

  return {
    user,
    isAuthenticated: Boolean(accessToken && user),
    isBootstrapping,
    logout: () => logoutMutation.mutate(),
  }
}
